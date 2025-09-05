# Código completo para descargar noticias y luego subirlas a pinecone
from datetime import date, timedelta
import os, argparse
from eventregistry import EventRegistry, QueryArticles, RequestArticlesInfo, ReturnInfo, ArticleInfoFlags
from pinecone import Pinecone
from utils import create_directory, exists_articles, save_article_to_json, collect_jsonl_strings, cleanup


parser = argparse.ArgumentParser(description="Descargar noticias y subirlas a Pinecone")
parser.add_argument("--concept", required=True, help="Concepto para buscar noticias (ej: 'Donald Trump')")
parser.add_argument("--page", default=1, type=int, help="Número de página para la búsqueda de noticias")
args = parser.parse_args()


# Inicializa los clientes EventRegistry y Pinecone
NEWS_API_KEY = os.environ["NEWS_API_KEY"]
er = EventRegistry(apiKey = NEWS_API_KEY)
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
pc = Pinecone(api_key=PINECONE_API_KEY)

# Estructura de la query
q = QueryArticles(
    lang = ["spa"], # consultas solo en español
    dateStart = date.today() - timedelta(days=30), dateEnd = date.today(), # las fechas tienen que estar contenidas en el último mes para la API gratuita
    keywords = args.concept.split(",")) # Tema de consulta

# Devuelve una lista de los 100 artículos principales, incluidos los conceptos, categorías e imágenes de los artículos. page=1 si es la primera consulta
q.setRequestedResult(RequestArticlesInfo(page = args.page, count = 100,
    returnInfo = ReturnInfo(articleInfo = ArticleInfoFlags()))) 
res = er.execQuery(q)


# Creo un directorio para almacenar los artículos si no existe
output_dir = "download_news"
create_directory(output_dir)

# Verifica si se encontraron artículos y los guarda en json
if exists_articles(res):
    articles = res["articles"]["results"]
    print(f"Found {len(articles)} articles about {args.concept}.")
    for i, article in enumerate(articles):
        save_article_to_json(article, output_dir)
else:
    print("No se encontraron artículos válidos para tu consulta.")

print(f"\nTodos los artículos procesados. Revisa el directorio '{output_dir}'.")


# En mi caso el índice ya estaba creado pero está bien tener el código aquí
index_name = "news"
if not pc.has_index(index_name):
    pc.create_index_for_model(
        name=index_name,
        cloud="aws",
        region="us-east-1",
        embed={
            "model":"llama-text-embed-v2",
            "field_map":{"text": "body"}
        }
    )

index = pc.Index("news")
NAMESPACE_NAME = "__default__"


# Recojo todos los strings JSONL de los archivos en el directorio de salida
records = collect_jsonl_strings(output_dir)

# Define el tamaño del lote para la inserción, 96 es el máximo pero depende del modelo
# Como no sé realmente el tamaño del lote permitido para cada modelo, usaré un tamaño de lote de 50 para evitar exceder el límite del modelo e iré iterando
batch_size = 50
for i in range(0, len(records), batch_size):
    index.upsert_records(namespace=NAMESPACE_NAME, records=records[i:i + batch_size])


# Limpiar la carpeta de salida porque ya no la necesito
cleanup(output_dir)
