Para reconstruir el contenedor:
docker compose up -d --build rag-api

Para abrir la terminal del contenedor:
docker exec -it rag-api bash

python model.py --query "Putin está relacionado con Trump?"
Fuera del contenedor:
docker compose exec rag-api python model.py --query "Putin está relacionado con Trump?" 


Al ejecutar me aparecen una serie de avisos, entre los cuales me dice que la ejecución se realizará en CPU porque no ha detectado GPU. Esto realentiza el modelo NER.

Las consultas de personas poniendo nombre y apellido mejoran considerablemente el modelo:
docker compose exec rag-api python model.py --query "Rosario ha hablado sobre un paso a desnivel?"
docker compose exec rag-api python model.py --query "Rosario Murillo ha hablado sobre un paso a desnivel?"
En el primero me aparece de OpenSanctions Rosario Rodríguez, político mejicana.