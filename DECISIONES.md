
# Decisiones técnicas - NovaMercado

## 1. Contrato de datos

La API implementa reglas de validación y normalización para las solicitudes de predicción y observaciones.

- Se normalizan identificadores de tienda representados como texto o con prefijo `T`.
- Se aceptan fechas inequívocas y nombres equivalentes de familias.
- Se convierten números enteros representados como texto cuando corresponde.
- Las familias omitidas generan advertencias y se completan utilizando promoción cero.
- Las ventas netas negativas se conservan para auditoría, acompañadas de una advertencia.
- Se rechazan tiendas o familias desconocidas, duplicados contradictorios, valores no finitos y promociones negativas.

Las solicitudes se registran mediante un esquema append-only. Las observaciones utilizan una operación upsert, identificadas por la combinación de tienda, fecha y familia.

## 2. Modelado y validación

### Modelo de referencia

Se utiliza la mediana histórica de ventas por tienda y familia como baseline.

### Modelo predictivo

Se utiliza `HistGradientBoostingRegressor`, considerando variables de calendario, tienda, familia, promociones y eventos aplicables.

Se evita utilizar variables rezagadas que puedan incorporar información futura. Los eventos considerados deben ser conocidos antes de realizar la predicción.

### Cantidad sugerida

La cantidad sugerida se calcula aplicando a la predicción un factor específico por familia. Dicho factor se selecciona minimizando el costo evaluado durante la validación.

### Validación temporal

El entrenamiento inicial utiliza los últimos 45 días disponibles como ventana de validación.

La evaluación debe respetar el orden temporal para evitar incorporar información futura.

## 3. Registro y disponibilidad del modelo

MLflow administra el registro de modelos mediante el nombre `novamercado-ventas`.

La versión utilizada para las predicciones se identifica mediante el alias `champion`.

Durante las pruebas realizadas se verificó que el alias `champion` correspondía a la versión 1.

La API conserva una copia local del modelo para permitir la continuidad de las predicciones ante interrupciones temporales de MLflow.

También se contempla la revisión periódica del alias para identificar nuevas versiones promovidas.

## 4. Reentrenamiento y promoción

El proceso de reentrenamiento está orquestado mediante el DAG `novamercado_retrain` de Apache Airflow.

El proceso permite generar un modelo candidato, registrar sus resultados y evaluar su posible promoción.

### Criterios de promoción

Para considerar la promoción de un candidato se requiere:

- Disponer de al menos 50 observaciones prospectivas.
- Contar con observaciones distribuidas en un mínimo de 7 días.
- Comparar el candidato y el modelo vigente sobre una misma muestra de evaluación.
- Obtener una mejora mínima del 2 % en el costo evaluado.

Si no se cumplen los requisitos, se conserva la versión `champion` vigente.

### Resultado observado

En las pruebas realizadas, el reentrenamiento finalizó correctamente, pero no promovió una nueva versión.

Se disponía únicamente de dos observaciones correspondientes a un día, por lo que no se cumplían los requisitos mínimos para una evaluación prospectiva suficiente.

Este comportamiento permite evitar promociones basadas en evidencia insuficiente.

## 5. Arquitectura operativa

El servicio utiliza Docker Compose para integrar:

- FastAPI como interfaz REST.
- PostgreSQL como almacenamiento de datos de producto.
- MLflow para el registro y administración de versiones.
- Apache Airflow 3 para la orquestación.
- Servicios de inicialización para preparar las dependencias y el modelo inicial.

Se verificó el despliegue utilizando volúmenes Docker nuevos.

Los servicios de inicialización pueden finalizar con código cero después de completar sus tareas.

## 6. Verificación del sistema

La solución cuenta con 15 pruebas automatizadas:

| Componente | Pruebas |
|---|---:|
| Contrato de datos | 6 |
| FastAPI | 3 |
| PostgreSQL | 3 |
| Airflow y MLflow | 3 |
| **Total** | **15** |

La ejecución completa de pytest finalizó con 15 pruebas aprobadas.

También se comprobaron manualmente:

- La generación de predicciones con el modelo registrado.
- La persistencia de observaciones en PostgreSQL.
- La ejecución del DAG de reentrenamiento.
- El registro de versiones en MLflow.
- La continuidad de las predicciones durante una interrupción temporal de MLflow.
- La inicialización del sistema con volúmenes nuevos.

## 7. Limitaciones y mejoras futuras

- Las observaciones no incorporan directamente la información de promociones. Durante el reentrenamiento se utiliza promoción cero cuando no existe información histórica disponible.
- Como mejora futura, podría recuperarse la información de promociones desde las solicitudes de predicción anteriores.
- Las pruebas automatizadas verifican contratos, conectividad e integración entre servicios, pero no sustituyen todas las pruebas de recuperación ante fallos ni una validación completa de rendimiento.
- La promoción de nuevas versiones requiere acumular suficientes observaciones prospectivas para aplicar los criterios establecidos.

Estas limitaciones no impiden utilizar los componentes validados, pero deben considerarse al evolucionar el servicio.
