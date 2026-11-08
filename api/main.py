import json
import logging
import os
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
import joblib
import requests
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from novamercado.core import catalogs, sanitize, features
from novamercado.database import engine, init_db
from novamercado import registry

class RequestBody(BaseModel):
    model_config=ConfigDict(extra='allow')
    tienda_id: object|None=None
    fecha: object|None=None
    familias: list[dict]|None=None
    ventas: list[dict]|None=None

state={'model':None,'version':None,'mlflow_ok':False,'airflow_ok':False}
lock=threading.RLock()

def refresh():
    while True:
        try:
            mv=registry.champion();state['mlflow_ok']=True
            if state['version']!=str(mv.version):
                path=registry.download(mv.version)
                bundle=joblib.load(path)
                with lock:state['model']=bundle;state['version']=str(mv.version)
        except Exception:state['mlflow_ok']=False
        try:
            r=requests.get(os.getenv('AIRFLOW_URL','http://airflow-api-server:8080')+'/api/v2/version',timeout=4)
            state['airflow_ok']=r.status_code<500
        except Exception:state['airflow_ok']=False
        time.sleep(15)

@asynccontextmanager
async def lifespan(app):
    init_db()
    threading.Thread(target=refresh,daemon=True).start()
    yield

app=FastAPI(title='NovaMercado - Laboratorio 2',lifespan=lifespan)
logger=logging.getLogger(__name__)

def clean(body,kind):
    try:return sanitize(body.model_dump(exclude_none=True),kind)
    except (ValueError,TypeError) as exc:raise HTTPException(422,detail=str(exc)) from exc

def record_request(kind,payload,quality):
    uid=str(uuid.uuid4())
    with engine.begin() as c:
        c.execute(text('INSERT INTO solicitudes(id,tipo,tienda_id,fecha,payload,calidad) VALUES(:id,:tipo,:tienda,:fecha,:payload,:calidad)'),{'id':uid,'tipo':kind,'tienda':payload['tienda_id'],'fecha':payload['fecha'],'payload':json.dumps(payload),'calidad':json.dumps(quality)})
    return uid

@app.post('/v1/prediccion')
def predict(body:RequestBody):
    p,q=clean(body,'prediccion')
    with lock:bundle=state['model'];version=state['version']
    if bundle is None:raise HTTPException(503,'modelo no disponible')
    frame=pd.DataFrame([{'fecha':p['fecha'],'tienda_id':p['tienda_id'],**f} for f in p['familias']]);cat=catalogs()
    try:pred=bundle['model'].predict(features(frame,cat))
    except Exception as exc:raise HTTPException(503,detail='modelo temporalmente no disponible') from exc
    result=[{'familia_id':f,'venta_esperada':round(max(0.,float(v)),2),'cantidad_sugerida':max(0,__import__('math').ceil(max(0.,float(v))*bundle['factors'].get(f,1.)))} for f,v in zip(frame.familia_id,pred)]
    uid=record_request('prediccion',p,q)
    with engine.begin() as c:
        for row in result:c.execute(text('INSERT INTO predicciones(solicitud_id,familia_id,venta_esperada,cantidad_sugerida,version_modelo) VALUES(:uid,:f,:v,:s,:m)'),{'uid':uid,'f':row['familia_id'],'v':row['venta_esperada'],'s':row['cantidad_sugerida'],'m':version})
    return {'tienda_id':p['tienda_id'],'fecha':p['fecha'],'version_modelo':version,'predicciones':result,'calidad':q}

@app.post('/v1/observaciones')
def observations(body:RequestBody):
    p,q=clean(body,'observaciones');changed=0
    record_request('observaciones',p,q)
    with engine.begin() as c:
        for row in p['ventas']:
            params={'t':p['tienda_id'],'d':p['fecha'],'f':row['familia_id'],'v':row['ventas']}
            old=c.execute(text('SELECT ventas FROM observaciones WHERE tienda_id=:t AND fecha=:d AND familia_id=:f'),params).scalar()
            if old is None:
                c.execute(text('INSERT INTO observaciones(tienda_id,fecha,familia_id,ventas) VALUES(:t,:d,:f,:v)'),params);changed+=1
            elif old!=params['v']:
                c.execute(text('UPDATE observaciones SET ventas=:v WHERE tienda_id=:t AND fecha=:d AND familia_id=:f'),params);changed+=1
    return {'registros_guardados':changed,'calidad':q}

@app.get('/modelo')
def model_info():
    if state['model'] is None:raise HTTPException(503,'modelo no disponible')
    return {'nombre':registry.NAME,'alias':'champion','version':state['version']}

@app.get('/health')
def health():
    if state['model'] is None:raise HTTPException(503,'modelo no disponible')
    problems=[]
    try:
        with engine.connect() as c:c.execute(text('SELECT 1'))
    except Exception:problems.append('base de datos')
    # Check MLflow directly with a short timeout. The background refresh may be
    # blocked in SDK retries, so its cached flag can be stale during outages.
    mlflow_url = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000').rstrip('/')
    try:
        response = requests.get(f'{mlflow_url}/health', timeout=2)
        if response.status_code != 200:
            problems.append('mlflow')
    except requests.RequestException:
        problems.append('mlflow')
    if not state['airflow_ok']:problems.append('airflow')
    return {'estado':'degradado' if problems else 'ok',**({'motivo':', '.join(problems)} if problems else {})}

@app.post('/admin/reentrenar',status_code=202)
def retrain():
    runid='manual__'+uuid.uuid4().hex
    base=os.getenv('AIRFLOW_URL','http://airflow-api-server:8080')
    try:
        token_response=requests.post(
            base+'/auth/token',
            json={'username':os.getenv('AIRFLOW_USER','admin'),
                  'password':os.getenv('AIRFLOW_PASSWORD','admin')},
            timeout=8,
        )
        token_response.raise_for_status()
        token=token_response.json()['access_token']
        response=requests.post(
            base+'/api/v2/dags/novamercado_retrain/dagRuns',
            json={'dag_run_id':runid,'logical_date':None,'conf':{}},
            headers={'Authorization':f'Bearer {token}'},
            timeout=8,
        )
        if not response.ok:
            logger.error('Airflow DAG trigger failed: HTTP %s: %s', response.status_code, response.text[:1500])
        response.raise_for_status()
    except Exception as exc:
        logger.exception('Airflow reentrenamiento fallido')
        raise HTTPException(503,'No se pudo iniciar reentrenamiento en Airflow') from exc
    with engine.begin() as c:c.execute(text('INSERT INTO entrenamientos(id,estado) VALUES(:id,:s)'),{'id':runid,'s':'en_curso'})
    return {'id':runid}

def reconcile_failed_run(runid: str) -> None:
    """Reconcile failures that occur before the retraining task executes."""
    base = os.getenv('AIRFLOW_URL', 'http://airflow-api-server:8080')
    try:
        auth_response = requests.post(
            base + '/auth/token',
            json={
                'username': os.getenv('AIRFLOW_USER', 'admin'),
                'password': os.getenv('AIRFLOW_PASSWORD', 'admin'),
            },
            timeout=5,
        )
        auth_response.raise_for_status()
        token = auth_response.json()['access_token']
        run_response = requests.get(
            base + '/api/v2/dags/novamercado_retrain/dagRuns/' + runid,
            headers={'Authorization': f'Bearer {token}'},
            timeout=5,
        )
        run_response.raise_for_status()
        if run_response.json().get('state') != 'failed':
            return
        # A failed DAG must never leave its associated product run in progress.
        # Preserve the existing champion; do not infer any promotion.
        version = state['version']
        try:
            version = str(registry.champion().version)
        except Exception:
            logger.warning('Unable to fetch champion when reconciling %s', runid)
        with engine.begin() as connection:
            connection.execute(
                text("""
                    UPDATE entrenamientos
                       SET estado = 'fallido', promovido = :promovido,
                           version = :version, motivo = :motivo
                     WHERE id = :id AND estado = 'en_curso'
                """),
                {
                    'id': runid,
                    'promovido': False,
                    'version': version,
                    'motivo': 'Airflow terminó con estado failed; revisar logs de la tarea',
                },
            )
    except (requests.RequestException, KeyError, ValueError) as exc:
        logger.warning('No se pudo sincronizar el estado de %s: %s', runid, exc)


@app.get('/admin/reentrenar/{runid}')
def retrain_status(runid: str):
    with engine.connect() as connection:
        row = connection.execute(
            text('SELECT estado,promovido,version,motivo FROM entrenamientos WHERE id=:id'),
            {'id': runid},
        ).first()
    if row is None:
        raise HTTPException(404, 'ejecución desconocida')
    if row[0] == 'en_curso':
        reconcile_failed_run(runid)
        with engine.connect() as connection:
            row = connection.execute(
                text('SELECT estado,promovido,version,motivo FROM entrenamientos WHERE id=:id'),
                {'id': runid},
            ).first()
    result = {'estado': row[0]}
    if row[0] != 'en_curso':
        result.update({'promovido': bool(row[1]), 'version': row[2], 'motivo': row[3]})
    return result
