The script news_to_pinecone downloads news from news.ai through the api eventregistry and storage the news in Pinecone.

Para reconstruir el contenedor:
docker exec -it news-ingest bash

Para realizar una subida:
python news_to_pinecone.py --concept "Hezbollah" --page "1"

NOTA: Los metadatos que se suben a Pinecone deben tener un máximo de 40KB. Problema: body me lo sube como metadata.