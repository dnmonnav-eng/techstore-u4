#TechStore U4-Implementación del núcleo de negocio

## Estructura del Proyecto

techstore-u4/
│
├── app/
│   ├── __init__.py
│   ├── api.py            #Controlador REST con FastAPI y manejo de excepciones
│   ├── domain.py         #Entidades, Value Objects, Agregados y Máquina de Estados
│   └── specifications.py #Patrón Especificación para reglas de descuento
│
├── datos/
│   ├── clientes.csv
│   ├── detalle_pedidos.csv
│   ├── escenarios.csv
│   ├── pedidos.csv
│   └── productos.csv
│
├── tests/
│   └── test_techstore.py #Pruebas con pytest
│
├── cargar_csv.py         #Cargador de fixtures e ingestión de datos iniciales
├── prueba_escenarios.py  #Script de validación automatizada de los escenarios E01–E15
└── README.md