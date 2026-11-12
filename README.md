
# NovaMercado - Laboratorio 2

## Descripción del proyecto

Servicio de Machine Learning en producción para el pronóstico diario de ventas de NovaMercado.

La solución integra FastAPI, PostgreSQL, MLflow, Apache Airflow y Docker Compose para ofrecer predicciones, almacenar observaciones reales, administrar versiones del modelo y ejecutar procesos de reentrenamiento.

## Arquitectura

El sistema está compuesto por los siguientes servicios:

| Componente | Tecnología | Responsabilidad |
|---|---|---|
| API de predicción | FastAPI | Exponer los endpoints de predicción, observaciones y administración |
| Base de datos de producto | PostgreSQL | Almacenar solicitudes, predicciones, observaciones y entrenamientos |
| Registro de modelos | MLflow | Administrar versiones del modelo y el alias `champion` |
| Orquestación | Apache Airflow | Ejecutar el flujo de reentrenamiento |
| Contenedores | Docker Compose | Desplegar y conectar los servicios |

La API utiliza el modelo registrado como `champion` en MLflow para realizar pronósticos.

El proceso de reentrenamiento permite generar modelos candidatos y evaluar si cumplen los criterios establecidos antes de promover una nueva versión.

## Requisitos

- Docker Desktop con el motor de contenedores activo.
- Docker Compose.
- Git.
- Windows PowerShell para ejecutar los comandos de esta guía.

## Preparación del entorno

### 1. Obtener el proyecto

Clonar el repositorio:

```powershell
git clone https://github.com/sofiaesc07/novamercado-ml-produccion.git
cd novamercado-ml-produccion
```

### 2. Preparar los datos

Verificar la presencia de los archivos CSV de entrada en `data/raw/`:

- `tiendas.csv`
- `familias.csv`
- `costos.csv`
- `feriados.csv`
- `historico_ventas.csv`

### 3. Configurar variables de entorno

Crear el archivo `.env` a partir del ejemplo:

```powershell
Copy-Item .env.example .env
```

Revisar las variables y configurar las contraseñas correspondientes.

No incluir el archivo `.env` con credenciales reales en los commits.

### 4. Construir e iniciar los servicios

Desde la raíz del proyecto:

```powershell
docker compose up -d --build
```

Verificar los contenedores:

```powershell
docker compose ps -a
```

Los servicios de inicialización, como `airflow-init` y `bootstrap`, pueden finalizar con estado `Exited (0)` después de completar correctamente sus tareas.

### 5. Verificar la API

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

Una respuesta saludable presenta:

```json
{
  "estado": "ok"
}
```

### 6. Interfaces disponibles

| Servicio | Dirección local |
|---|---|
| FastAPI Swagger | http://localhost:8000/docs |
| FastAPI Health | http://localhost:8000/health |
| MLflow | http://localhost:5000 |
| Airflow | http://localhost:8080 |

## Endpoints principales

- `POST /v1/prediccion`
- `POST /v1/observaciones`
- `POST /admin/reentrenar`
- `GET /admin/reentrenar/{id}`
- `GET /modelo`
- `GET /health`

## Documentación adicional

Consultar `DECISIONES.md` para las decisiones técnicas, limitaciones y criterios del ciclo de vida del modelo.
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
