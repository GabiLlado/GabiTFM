Para reconstruir el contenedor:
docker compose up -d --build rag-api

Para abrir la temrinal del contenedor:
docker exec -it rag-api bash

python model.py --query "Putin está relacionado con Trump?"