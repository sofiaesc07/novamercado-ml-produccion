# Catálogo de errores de ejemplo

Las solicitudes que recibe el servicio provienen de los sistemas de cada tienda.
No todas llegan en buen estado. Este catálogo muestra **ejemplos** de problemas
que ya se han observado. No es una lista completa: en operación pueden llegar
otros problemas.

Para cada tipo de problema, el servicio debe decidir una política y justificarla:

- **Reparar:** la corrección es inequívoca y se informa en `calidad`.
- **Predecir con advertencia:** se responde, pero se informa qué se supuso.
- **Rechazar:** se responde con un error 422 que explique el motivo.

Cada ejemplo tiene un archivo en `ejemplos/errores/`.

## Solicitudes de predicción (`POST /v1/prediccion`)

| Código | Problema | Ejemplo |
|---|---|---|
| E01 | Identificador de tienda como texto o con prefijo | `"tienda_id": "T05"`, `"tienda_id": "5"` |
| E02 | Familia escrita de otra forma | `"LÁCTEOS"`, `"lacteos "`, `"Frutas y Verduras"` |
| E03 | Cantidad en promoción como texto o decimal | `"en_promocion": "3"`, `"en_promocion": 2.0` |
| E04 | Fecha en otro formato | `"2025-11-17T00:00:00"`, `"17/11/2025"` |
| E05 | Faltan familias que la tienda vende | La lista trae 10 de las 12 familias |
| E06 | Familia repetida con valores distintos | `abarrotes` aparece dos veces |
| E07 | Nombre de campo distinto al del contrato | `"tienda"` en vez de `"tienda_id"` |

## Observaciones de ventas (`POST /v1/observaciones`)

| Código | Problema | Ejemplo |
|---|---|---|
| E08 | Ventas negativas | `"ventas": -4` (devoluciones registradas como venta) |
| E09 | Envío repetido del mismo día y tienda | La misma observación llega dos veces |
| E10 | Número con separador de miles o coma decimal | `"ventas": "1,234"`, `"ventas": "812,0"` |
