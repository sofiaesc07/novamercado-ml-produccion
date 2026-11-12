"""Pruebas de integración de solo lectura: Airflow, MLflow y API.

Requieren servicios de Docker Compose iniciados. No activan DAGs,
no registran modelos y no modifican el alias champion.
"""

import os

import pytest
import requests
from mlflow.tracking import MlflowClient


AIRFLOW_URL = os.getenv("INTEGRATION_AIRFLOW_URL", "http://airflow-api-server:8080").rstrip("/")
API_URL = os.getenv("INTEGRATION_BASE_URL", "").rstrip("/")
MODEL_NAME = "novamercado-ventas"


@pytest.fixture(scope="module")
def http():
    session = requests.Session()
    session.trust_env = False
    yield session
    session.close()


def test_airflow_api_disponible(http):
    """El servicio HTTP de Airflow 3 responde desde la red Compose."""
    response = http.get(f"{AIRFLOW_URL}/api/v2/version", timeout=15)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "version" in data and str(data["version"]).startswith("3.")


def test_mlflow_champion_registrado():
    """MLflow permite resolver el alias champion a una versión registrada."""
    model = MlflowClient().get_model_version_by_alias(MODEL_NAME, "champion")
    assert model.name == MODEL_NAME
    assert int(model.version) >= 1
    assert model.source  # el registro contiene la ruta del artefacto


@pytest.mark.skipif(not API_URL, reason="Definir INTEGRATION_BASE_URL para validar API vs MLflow")
def test_api_coincide_con_champion_mlflow(http):
    """La versión expuesta por la API coincide con el registro champion."""
    model = MlflowClient().get_model_version_by_alias(MODEL_NAME, "champion")
    response = http.get(f"{API_URL}/modelo", timeout=15)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["nombre"] == MODEL_NAME
    assert data["alias"] == "champion"
    assert str(data["version"]) == str(model.version)
