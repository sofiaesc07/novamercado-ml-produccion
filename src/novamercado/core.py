import math
import re
import unicodedata
from datetime import datetime, date
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parents[2] / 'data' / 'raw'

def catalogs():
    return {k: pd.read_csv(DATA / (k + '.csv')) for k in ('tiendas','familias','costos','feriados')}

def normalized(value):
    value = unicodedata.normalize('NFKD', str(value).strip().lower())
    return re.sub(r'[^a-z0-9]', '', ''.join(c for c in value if not unicodedata.combining(c)))

def clean_date(value):
    if not isinstance(value, str):
        raise ValueError('fecha debe ser texto')
    for fmt in ('%Y-%m-%d','%Y-%m-%dT%H:%M:%S','%d/%m/%Y'):
        try:
            d=datetime.strptime(value,fmt)
            if fmt.endswith('%H:%M:%S') and d.time().isoformat() != '00:00:00':
                raise ValueError('fecha con hora no nula')
            return d.date().isoformat()
        except ValueError:
            pass
    raise ValueError('fecha inválida')

def integer(value, field, allow_negative=False):
    if isinstance(value,bool): raise ValueError(f'{field}: booleano no válido')
    if isinstance(value,str):
        v=value.strip()
        if re.fullmatch(r'\d{1,3}(,\d{3})+',v): v=v.replace(',','')
        elif re.fullmatch(r'\d+,0+',v): v=v.split(',')[0]
        value=v
    try: n=float(value)
    except (ValueError,TypeError): raise ValueError(f'{field}: número inválido')
    if not math.isfinite(n) or not n.is_integer() or (n<0 and not allow_negative):
        raise ValueError(f'{field}: se requiere entero no negativo')
    return int(n)

def sanitize(payload, kind='prediccion', cat=None):
    cat=cat or catalogs(); p=dict(payload); notes=[]
    def note(field, action, detail): notes.append({'campo':field,'accion':action,'detalle':detail})
    if 'tienda_id' not in p and 'tienda' in p:
        p['tienda_id']=p['tienda'];note('tienda_id','reparar','campo tienda renombrado')
    raw=p.get('tienda_id')
    if isinstance(raw,str) and re.fullmatch(r'[tT]\d+',raw.strip()): raw=raw.strip()[1:]
    store=integer(raw,'tienda_id')
    if store not in set(cat['tiendas'].tienda_id):raise ValueError('tienda_id desconocida')
    if p.get('tienda_id') != store:note('tienda_id','reparar',f'identificador normalizado a {store}')
    datevalue=clean_date(p.get('fecha'))
    if p.get('fecha')!=datevalue:note('fecha','reparar','fecha convertida a AAAA-MM-DD')
    key='familias' if kind=='prediccion' else 'ventas'
    if not isinstance(p.get(key),list) or not p[key]:raise ValueError(f'{key}: lista no vacía requerida')
    aliases={normalized(row.familia_id):row.familia_id for row in cat['familias'].itertuples()}
    aliases.update({normalized(row.nombre):row.familia_id for row in cat['familias'].itertuples()})
    result={}
    for i,item in enumerate(p[key]):
        if not isinstance(item,dict):raise ValueError(f'{key}[{i}]: objeto requerido')
        original=item.get('familia_id');family=aliases.get(normalized(original))
        if family is None:raise ValueError(f'{key}[{i}].familia_id desconocida')
        if original!=family:note(f'{key}[{i}].familia_id','reparar',f'{original} interpretado como {family}')
        field='en_promocion' if kind=='prediccion' else 'ventas'
        number=integer(item.get(field),f'{key}[{i}].{field}',allow_negative=kind=='observaciones')
        if number<0:
            note(f'{key}[{i}].ventas','advertir','venta negativa conservada como ajuste neto')
        elif item.get(field)!=number:note(f'{key}[{i}].{field}','reparar',f'convertido a {number}')
        if family in result:
            if result[family]!=number:raise ValueError(f'{key}: familia {family} repetida con valores distintos')
            note(f'{key}[{i}]','reparar','duplicado idéntico eliminado')
        result[family]=number
    if kind=='prediccion':
        missing=set(cat['familias'].familia_id)-set(result)
        for family in sorted(missing):
            result[family]=0;note(f'familias.{family}','advertir','familia omitida: se supone promoción cero')
    quality='advertencia' if any(x['accion']=='advertir' for x in notes) else ('corregido' if notes else 'ok')
    return {'tienda_id':store,'fecha':datevalue,key:[{'familia_id':f,('en_promocion' if kind=='prediccion' else 'ventas'):v} for f,v in result.items()]}, {'estado':quality,'observaciones':notes}

def features(frame, cat):
    df=frame.copy();df['fecha']=pd.to_datetime(df['fecha']);df['dia_semana']=df.fecha.dt.dayofweek
    df['mes']=df.fecha.dt.month;df['dia_mes']=df.fecha.dt.day;df['dia_ano']=df.fecha.dt.dayofyear
    stores=cat['tiendas'].set_index('tienda_id')
    df['ciudad']=df.tienda_id.map(stores.ciudad)
    holidays=cat['feriados'].copy();holidays['fecha']=pd.to_datetime(holidays.fecha)
    relevant=holidays[['fecha','ambito']].drop_duplicates()
    national=set(relevant.loc[relevant.ambito=='nacional','fecha'])
    local=set(zip(relevant.fecha,relevant.ambito))
    df['evento']=[int(dt in national or (dt,city) in local) for dt,city in zip(df.fecha,df.ciudad)]
    fam={f:i for i,f in enumerate(sorted(cat['familias'].familia_id))}
    df['familia_num']=df.familia_id.map(fam)
    df['tienda_id']=df.tienda_id.astype(int)
    return df[['tienda_id','familia_num','en_promocion','dia_semana','mes','dia_mes','dia_ano','evento']]

def business_cost(y, suggestion, family, cat):
    costs=cat['costos'].set_index('familia_id');import numpy as np
    cf=np.array([costs.loc[f,'costo_faltante'] for f in family]);cs=np.array([costs.loc[f,'costo_sobrante'] for f in family]);y=np.asarray(y);s=np.asarray(suggestion)
    return float(np.mean(cf*np.maximum(y-s,0)+cs*np.maximum(s-y,0)))
