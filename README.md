
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

## Pruebas automatizadas

El proyecto cuenta con 15 pruebas automatizadas que verifican el contrato de entrada y la integración entre los principales componentes.

| Archivo | Cantidad | Validación |
|---|---:|---|
| `tests/test_contract.py` | 6 | Validación y normalización de solicitudes |
| `tests/test_integration_api.py` | 3 | Disponibilidad del modelo, predicción y manejo de errores HTTP |
| `tests/test_integration_postgres.py` | 3 | Conexión, esquema e integridad de PostgreSQL |
| `tests/test_integration_orchestration.py` | 3 | Disponibilidad de Airflow, registro en MLflow y consistencia de `champion` |

### Ejecutar todas las pruebas

Con los servicios de Docker Compose en funcionamiento:

```powershell
docker compose up -d
docker compose build api
docker compose run --rm --no-deps `
    -e INTEGRATION_BASE_URL=http://api:8000 `
    --entrypoint python api -m pytest /app/tests -v
```

### Resultado verificado

En la ejecución de validación se obtuvo:

```text
15 passed, 1 warning in 2.57s
```

La advertencia corresponde al uso de configuración de Pydantic que está deprecada. No impidió la ejecución de las pruebas.

Las pruebas de integración requieren que los servicios estén activos. No realizan un reentrenamiento nuevo ni promueven una versión del modelo.

## Uso de la API

La documentación interactiva está disponible en `http://localhost:8000/docs`.

| Método | Endpoint | Propósito |
|---|---|---|
| POST | `/v1/prediccion` | Generar pronósticos de ventas |
| POST | `/v1/observaciones` | Registrar observaciones de ventas reales |
| POST | `/admin/reentrenar` | Solicitar un reentrenamiento |
| GET | `/admin/reentrenar/{id}` | Consultar el estado de un reentrenamiento |
| GET | `/modelo` | Consultar la versión del modelo en servicio |
| GET | `/health` | Consultar el estado de salud del servicio |

### Consultar el modelo en servicio

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/modelo"
```

### Consultar la salud del servicio

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

Las solicitudes de predicción y observaciones pueden ejecutarse desde Swagger utilizando los esquemas definidos en la API.
