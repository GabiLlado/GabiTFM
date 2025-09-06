---
# Gestión del Contenedor `client`

Este documento describe la estructura y propósito de los archivos clave dentro de la carpeta `client`, que gestiona las operaciones y la configuración del contenedor `client`.

---
## `client/`

La carpeta `client/` es el centro de control para todo lo relacionado con el **contenedor `client`**. Este contenedor se conecta a otros servicios para ejecutar consultas y procesar datos.
Para ver el estado de los contenedores ejecuto: docker ps. Solo aparecen los que están corriendo.
Si client está corriendo y quiero ejecutar algo desde el propio contenedor, ejecuto docker exec -it yente-client-1 bash.
Para abrir archivo en terminal: cat archivo.
Para salir del contenedor: exit.


---
### `script_queries/`

Aquí se almacenan todos los **scripts de consulta** que deseas ejecutar dentro del contenedor `client`. Al iniciar el contenedor, estos scripts se copian automáticamente a la carpeta correspondiente dentro del mismo, listos para su ejecución.
Para ejecutar una query:
python yente_search1.py --query "Vladimir Putin" --dataset "default" --limit 10

---
### `output/`

Esta carpeta está dedicada a la **salida de las consultas**. Una vez que los scripts en `script_queries/` se ejecutan dentro del contenedor, los resultados generados se guardan en esta carpeta, permitiendo un fácil acceso a los datos procesados.

---
### `Dockerfile`

El `Dockerfile` es la **receta para construir la imagen de Docker** que se utiliza para crear el contenedor `client`. Define el entorno, las dependencias y la configuración inicial del contenedor.

---
### `requirements.txt`

Este archivo lista todas las **aplicaciones y dependencias** necesarias para que el contenedor `client` funcione correctamente. Cuando se construye el contenedor utilizando la imagen definida en `Dockerfile`, estas dependencias se instalan automáticamente.


--------------------------------------------------------------------------------------------------------------------------------

curl.exe -s "http://localhost:8000/search/default?q=Putin&limit=1" | ConvertFrom-Json | ConvertTo-Json > ejemplo