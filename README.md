# NovaMercado — Laboratorio 2

Servicio de pronóstico de ventas diarias con FastAPI, PostgreSQL, MLflow y Airflow.

## Preparación (Windows / PowerShell)
1. Instalar Docker Desktop y activar el motor.
2. Colocar los seis CSV publicados en `data/raw/`: `tiendas.csv`, `familias.csv`, `costos.csv`, `feriados.csv`, `historico_ventas.csv`.
3. Copiar `.env.example` a `.env` y cambiar todas las contraseñas.
4. Ejecutar `docker compose up --build -d` desde la raíz del repositorio.
5. Verificar `docker compose ps` y `docker compose logs bootstrap --tail 50`.
6. Probar `http://localhost:8000/health`, `http://localhost:8000/docs`, `http://localhost:5000` y `http://localhost:8080`.

## Pruebas locales
`py -m pip install -r requirements.txt`
`py -m pytest -q`

## Contrato
- POST `/v1/prediccion`
- POST `/v1/observaciones`
- POST `/admin/reentrenar`
- GET `/admin/reentrenar/{id}`
- GET `/modelo`
- GET `/health`

## Nota de desarrollo
Esta es una primera implementación que requiere integración y verificación con Docker antes de entregarse. Consultar `DECISIONES.md` para limitaciones y próximos ajustes.
