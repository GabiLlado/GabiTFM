import requests
import json
import os
import argparse
from datetime import datetime

# Configuración de la API de Yente
YENTE_BASE_URL = "http://app-1:8000" # URL del servicio Yente dentro de la red Docker Compose

# Directorio de salida dentro del contenedor
OUTPUT_DIR = "/app/results_queries" 

# El dataset puede ser default, sanctions o peps. Ver https://www.opensanctions.org/docs/api/matching/.
def perform_search(query, dataset="default", limit=10, include_dataset=None, exclude_dataset=None):
    """
    Realiza una consulta de búsqueda a la API de Yente.
    """
    search_url = f"{YENTE_BASE_URL}/search/{dataset}"
    params = {"q": query, "limit": limit}

    if include_dataset:
        params["scope"] = ",".join(include_dataset)
    if exclude_dataset:
        params["exclude"] = ",".join(exclude_dataset)

    print(f"Realizando consulta a: {search_url} con parámetros: {params}")

    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status() # Lanza una excepción para errores HTTP (4xx o 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con Yente o al realizar la consulta: {e}")
        return None

def save_results(data, query, dataset="default"):
    """
    Guarda los resultados de la consulta en un archivo JSON en la carpeta 'results'.
    """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR) # Crea el directorio si no existe

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Genera un nombre de archivo más legible, limpiando la query
    clean_query = "".join(c if c.isalnum() else "_" for c in query)
    filename = f"search_results_{clean_query}_{dataset}_{timestamp}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Resultados guardados exitosamente en: {filepath}")
        return filepath
    except IOError as e:
        print(f"Error al guardar los resultados en {filepath}: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Realiza una consulta a Yente y guarda los resultados.")
    parser.add_argument("-q", "--query", required=True, help="Término de búsqueda.")
    parser.add_argument("-d", "--dataset", default="default", help="Dataset de Yente a consultar (ej. 'default', 'sanctions').")
    parser.add_argument("-l", "--limit", type=int, default=1, help="Número máximo de resultados a devolver.")
    parser.add_argument("--include", nargs='*', help="Lista de datasets a incluir en el scope (separados por espacio).")
    parser.add_argument("--exclude", nargs='*', help="Lista de datasets a excluir del scope (separados por espacio).")

    args = parser.parse_args()

    # Realizar la búsqueda
    results = perform_search(
        query=args.query,
        dataset=args.dataset,
        limit=args.limit,
        include_dataset=args.include,
        exclude_dataset=args.exclude
    )

    if results:
        # Guardar los resultados
        save_results(results, args.query, args.dataset)
    else:
        print("No se pudieron obtener resultados de la consulta.")