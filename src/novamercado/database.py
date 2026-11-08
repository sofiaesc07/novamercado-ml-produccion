import os
from sqlalchemy import create_engine, text

engine=create_engine(os.getenv('DATABASE_URL','sqlite:////tmp/novamercado.db'),pool_pre_ping=True)

def init_db():
    with engine.begin() as c:
        c.execute(text('CREATE TABLE IF NOT EXISTS solicitudes (id VARCHAR(64) PRIMARY KEY, tipo VARCHAR(30), tienda_id INTEGER, fecha VARCHAR(10), payload TEXT, calidad TEXT, creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'))
        c.execute(text('CREATE TABLE IF NOT EXISTS predicciones (solicitud_id VARCHAR(64), familia_id VARCHAR(80), venta_esperada FLOAT, cantidad_sugerida INTEGER, version_modelo VARCHAR(30), PRIMARY KEY(solicitud_id,familia_id))'))
        c.execute(text('CREATE TABLE IF NOT EXISTS observaciones (tienda_id INTEGER, fecha VARCHAR(10), familia_id VARCHAR(80), ventas INTEGER, PRIMARY KEY(tienda_id,fecha,familia_id))'))
        c.execute(text('CREATE TABLE IF NOT EXISTS entrenamientos (id VARCHAR(100) PRIMARY KEY, estado VARCHAR(30), promovido BOOLEAN, version VARCHAR(30), motivo TEXT)'))
