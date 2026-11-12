"""Pruebas de integración de solo lectura para PostgreSQL de NovaMercado.

Ejecutar desde la red de Docker Compose con DATABASE_URL configurada.
No insertan, actualizan ni eliminan registros.
"""

import os

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


@pytest.fixture(scope="module")
def db():
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.fail("Falta DATABASE_URL para ejecutar las pruebas de integración")
    # No registrar la URL: puede contener credenciales.
    assert make_url(url).get_backend_name() == "postgresql"
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 10})
    try:
        yield engine
    finally:
        engine.dispose()


def test_postgresql_responde(db):
    """La aplicación puede conectarse a su base PostgreSQL."""
    with db.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar_one() == 1


def test_esquema_y_clave_primaria_observaciones(db):
    """El contrato de persistencia tiene columnas y PK compuesta esperadas."""
    inspector = inspect(db)
    assert "observaciones" in inspector.get_table_names(schema="public")
    columns = {c["name"]: c for c in inspector.get_columns("observaciones", schema="public")}
    assert {"tienda_id", "fecha", "familia_id", "ventas"}.issubset(columns)
    assert all(not columns[c]["nullable"] for c in ("tienda_id", "fecha", "familia_id"))
    pk = inspector.get_pk_constraint("observaciones", schema="public")
    assert set(pk["constrained_columns"]) == {"tienda_id", "fecha", "familia_id"}


def test_consulta_de_observaciones_sin_duplicados(db):
    """Se pueden consultar observaciones y no hay claves repetidas."""
    with db.connect() as conn:
        result = conn.execute(text("""
            SELECT tienda_id, fecha, familia_id, ventas
            FROM public.observaciones
            ORDER BY fecha DESC, tienda_id, familia_id
            LIMIT 5
        """))
        for row in result:
            assert isinstance(row.tienda_id, int)
            assert isinstance(row.fecha, str) and len(row.fecha) == 10
            assert isinstance(row.familia_id, str) and row.familia_id
            assert row.ventas is None or isinstance(row.ventas, int)

        duplicates = conn.execute(text("""
            SELECT 1 FROM public.observaciones
            GROUP BY tienda_id, fecha, familia_id
            HAVING COUNT(*) > 1
            LIMIT 1
        """)).first()
        assert duplicates is None
