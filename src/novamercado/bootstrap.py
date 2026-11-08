import os
import time
from pathlib import Path
from sqlalchemy import text
from novamercado.database import init_db,engine
from novamercado.training import train
from novamercado.registry import champion,publish,download

def main():
    for attempt in range(60):
        try:
            init_db();champion();print('Modelo existente: se conserva');return
        except Exception as exc:
            if attempt<5:time.sleep(3)
            elif attempt<10:time.sleep(5)
            else:break
    artifact,metrics=train();print('Métricas iniciales:',metrics,flush=True)
    for attempt in range(50):
        try:
            version=publish(artifact,metrics,initial=True);download(version)
            print('Champion inicial:',version,flush=True);return
        except Exception as exc:
            print('Esperando MLflow:',exc,flush=True);time.sleep(5)
    raise RuntimeError('No se pudo registrar el primer modelo')
if __name__=='__main__':main()
