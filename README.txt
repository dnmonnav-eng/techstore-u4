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


## Pasos de Instalación y Configuración
Clona o copia el repositorio en tu equipo local.   
Abre una terminal en la carpeta raíz del proyecto (techstore-u4).   
Crea y activa un entorno virtual de Python:   
 python -m venv .venv

Windows (PowerShell): 
 .venv\Scripts\Activate.ps1   
Windows (CMD): 
 .venv\Scripts\activate.bat   
macOS / Linux: 
source .venv/bin/activate   

Instala las dependencias requeridas:   
Bashpython -m pip install fastapi uvicorn pytest httpx

##Instrucciones de Ejecución
1. Carga de datos iniciales (Fixtures)
Para comprobar que la ingestión de los 16 pedidos desde los archivos CSV funciona correctamente:   Bashpython cargar_csv.py
2. Validación de escenarios de prueba (E01–E15)
Para ejecutar y verificar de forma automatizada los 15 casos de negocio y restricciones definidos en escenarios.csv:   Bashpython prueba_escenarios.py
3. Ejecución de pruebas unitarias con Pytest
Para correr la suite completa de pruebas automatizadas asegurando que las reglas y excepciones responden correctamente:   Bashpython -m pytest -v
4. Ejecución del Servidor API (FastAPI)
Para levantar el servidor web local y probar la interfaz REST:   Bashuvicorn app.api:app --reload

Una vez iniciado, abre tu navegador en http://127.0.0.1:8000/docs para interactuar con la documentación interactiva de Swagger
