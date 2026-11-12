"""Pruebas de integración HTTP contra una API NovaMercado ya iniciada.

Ejecutar con INTEGRATION_BASE_URL=http://api:8000 desde Docker Compose.
Sin esa variable, se omiten para no romper las pruebas unitarias.
"""

import os

import pytest
import requests


BASE_URL = os.getenv("INTEGRATION_BASE_URL", "").rstrip("/")
pytestmark = pytest.mark.skipif(
    not BASE_URL,
    reason="Definir INTEGRATION_BASE_URL para habilitar pruebas de integración",
)


@pytest.fixture(scope="module")
def api():
    session = requests.Session()
    session.trust_env = False
    yield session
    session.close()


def test_modelo_champion_disponible(api):
    response = api.get(f"{BASE_URL}/modelo", timeout=15)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["nombre"] == "novamercado-ventas"
    assert body["alias"] == "champion"
    assert str(body["version"]).isdigit()


def test_prediccion_real_con_modelo_registrado(api):
    payload = {
        "tienda_id": 5,
        "fecha": "2026-03-01",
        "familias": [
            {"familia_id": "abarrotes", "en_promocion": 0},
            {"familia_id": "bebidas", "en_promocion": 8},
        ],
    }
    response = api.post(f"{BASE_URL}/v1/prediccion", json=payload, timeout=30)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tienda_id"] == 5
    assert str(body["version_modelo"]).isdigit()
    assert body["predicciones"]
    names = {item["familia_id"] for item in body["predicciones"]}
    assert {"abarrotes", "bebidas"}.issubset(names)
    assert all(item["venta_esperada"] >= 0 for item in body["predicciones"])
    assert all(isinstance(item["cantidad_sugerida"], int) and item["cantidad_sugerida"] >= 0
               for item in body["predicciones"])


def test_solicitud_invalida_rechazada_con_422(api):
    payload = {
        "tienda_id": 5,
        "fecha": "2026-03-01",
        "familias": [{"familia_id": "abarrotes", "en_promocion": -1}],
    }
    response = api.post(f"{BASE_URL}/v1/prediccion", json=payload, timeout=15)
    assert response.status_code == 422, response.text
