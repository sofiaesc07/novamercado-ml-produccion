import os
from pathlib import Path
import joblib
import mlflow
from mlflow.tracking import MlflowClient

NAME='novamercado-ventas'
STORE=Path(os.getenv('MODEL_DIR','/app/model_store'))

def client():
    mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI','http://mlflow:5000'))
    return MlflowClient()

def champion():
    return client().get_model_version_by_alias(NAME,'champion')

def publish(artifact,metrics,initial=False):
    c=client();mlflow.set_experiment('NovaMercado pronostico diario')
    with mlflow.start_run() as run:
        mlflow.log_metrics({k:v for k,v in metrics.items() if isinstance(v,(int,float))})
        mlflow.log_params({'algoritmo':'HistGradientBoostingRegressor','validacion_desde':metrics['validacion_desde']})
        mlflow.log_artifact(str(artifact),artifact_path='bundle')
        uri=f'runs:/{run.info.run_id}/bundle/{artifact.name}'
        v=mlflow.register_model(uri,NAME)
    if initial:c.set_registered_model_alias(NAME,'champion',v.version)
    return str(v.version)

def download(version):
    c=client();mv=c.get_model_version(NAME,str(version))
    local=mlflow.artifacts.download_artifacts(artifact_uri=mv.source)
    path=STORE/f'champion_{version}.joblib';STORE.mkdir(exist_ok=True,parents=True)
    import shutil
    shutil.copyfile(local,path)
    return path
