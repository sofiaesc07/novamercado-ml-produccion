# Decisiones técnicas — NovaMercado

## Contrato
- Reparar tienda como texto o prefijo T, fechas inequívocas, nombres de familias equivalentes y números enteros representados como texto.
- Advertir por familias omitidas, usando promoción cero, y por ventas netas negativas (se conservan para auditoría).
- Rechazar tienda/familia desconocida, duplicados contradictorios, valores no finitos y promociones negativas.
- El registro de solicitudes es append-only; las observaciones son upsert por tienda, fecha y familia.

## Modelado
- Baseline: mediana histórica por tienda y familia.
- Modelo: HistGradientBoostingRegressor, con calendario, tienda, familia, promociones y eventos aplicables.
- Sin lags que puedan incorporar observaciones futuras. Los eventos se conocen de antemano.
- Cantidad sugerida: techo de predicción por factor de familia elegido minimizando el costo de validación.
- Validación: últimos 45 días del conjunto disponible.

## Promoción
- Se exige reducción de costo >=2% en la misma ventana de validación. Si la ventana cambia, se conserva el champion.
- Esta compuerta es conservadora y debe mejorarse con evaluación común del incumbent y challenger al añadir observaciones nuevas.
- Se conserva copia local del champion para interrupciones de MLflow y la API revisa el alias cada 15 segundos.

## Limitaciones identificadas
- Las observaciones no incluyen promociones; al reentrenar, se usa cero cuando no hay una promoción histórica disponible. Es preferible unirlas a la última solicitud de pronóstico previa.
- La integración con la autenticación de Airflow 3 debe comprobarse contra la imagen concreta en Docker.
- El servicio aún requiere pruebas end-to-end reales en Docker y una compuerta comparable al cambiar de ventana.
