from datetime import datetime
from airflow.sdk import dag, task

@dag(dag_id='novamercado_retrain',schedule=None,start_date=datetime(2024,1,1),catchup=False,tags=['novamercado'])
def novamercado_retrain():
    @task
    def retrain(**context):
        from novamercado.retrain import execute
        execute(context['run_id'])
    retrain()
novamercado_retrain()
