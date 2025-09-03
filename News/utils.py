import os, json, shutil


def create_directory(dir_path):
    """
    Crea un directorio si no existe.

    Params:
        dir_path (str): La ruta del directorio a crear.
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"Directorio creado: {dir_path}")
    else:
        print(f"El directorio ya existe: {dir_path}")



def exists_articles(res):
    """
    Verifica si existen artículos en la respuesta.

    Conditions:
    - 'res' es un diccionario que contiene la respuesta de la API.
    - La respuesta debe contener la clave "articles" y dentro de ella la clave "results".

    Params:
    - res (dict): La respuesta de la API que se va a verificar.

    Return:
    - bool: True si existen artículos, False en caso contrario.
    """
    return res and "articles" in res and "results" in res["articles"]



def save_article_to_json(article, output_dir):
    """
    Guarda un artículo en formato JSON en el directorio especificado.

    Params:
    - article (dict): El artículo a guardar.
    - output_dir (str): El directorio donde se guardará el artículo.

    Return:
    - None
    """
    article_id = article.get('uri')
    if not article_id:
        print(f"Omitiendo el artículo debido a la falta de ID.")
        return

    # Campos que quiero guardar en el json
    filtered_article = {
        "id": article.get("uri"),
        "lang": article.get("lang"),
        "dateTimePub": article.get("dateTimePub"),
        "url": article.get("url"),
        "title": article.get("title"),
        "body": article.get("body")
    }

    filename_json = os.path.join(output_dir, f"{article_id}.json")
    try:
        with open(filename_json, 'w', encoding='utf-8') as f:
            json.dump(filtered_article, f, indent=4, ensure_ascii=False)
        print(f"Artículo {article_id} guardado en {filename_json}")
    except Exception as e:
        print(f"Error al guardar el artículo {article_id} en JSON: {e}")



def collect_jsonl_strings(output_dir):
    """
    Reúne todas las cadenas JSONL de los archivos en el directorio de salida.

    Params:
    - output_dir (str): El directorio de salida donde se encuentran los archivos JSON.

    Return:
    - list: Una lista de cadenas JSONL.
    """
    records = []
    for filename in os.listdir(output_dir):
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'r', encoding='utf-8') as f_in:
            data = json.load(f_in)
            records.append(data)
    return records



def cleanup(output_dir):
    """
    Elimina el directorio de salida y su contenido.

    Params:
    - output_dir (str): El directorio de salida a eliminar.
    """
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
        print(f"[cleanup] Carpeta eliminada: {output_dir}")
