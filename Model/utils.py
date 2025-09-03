import os
import httpx
import asyncio
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore, PineconeEmbeddings
from langchain_openai import ChatOpenAI



def model_ini(model="gpt-4o-mini"):
    """
    Inicializa el modelo de lenguaje. Conexión por medio de la API de OpenAI.

    Conditions:
        - El modelo debe ser válido.
        - La clave de API de OpenAI debe estar configurada (es de pago).

    Params:
        model: El modelo de lenguaje a utilizar.

    Return:
        El modelo de lenguaje inicializado.
    """
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
    llm = ChatOpenAI(model=model, api_key=OPENAI_API_KEY)
    return llm



def retrieve_docs(num_docs):
    """
    Recupera documentos de Pinecone. Antes inicializa Pinecone y el índice.

    Conditions:
        - La clave de API de Pinecone debe estar configurada.
        - El índice de Pinecone debe existir.

    Params:
        num_docs: El número de documentos a recuperar.

    Return:
        Un objeto de recuperación de documentos.
    """
    PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(os.environ["PINECONE_INDEX"])

    embedding = PineconeEmbeddings(
        model=os.environ["PINECONE_EMBEDDING_MODEL"],
        api_key=PINECONE_API_KEY,
        query_params={"input_type": "query"},
        document_params={"input_type": "passage"},
    )
    vector_store = PineconeVectorStore(embedding=embedding, index=index, text_key="body")
    return vector_store.as_retriever(search_kwargs={"k": num_docs})



def format_docs(docs):
    """
    Formatea los documentos para el prompt.
    """
    return "\n\n".join(f"• {d.page_content}" for d in docs)



def extract_person_org(ner, text):
    """
    Extrae entidades de tipo persona y organización del texto.

    Conditions:
        - El modelo de NER debe estar inicializado.

    Params:
        ner: El modelo de NER inicializado.
        text: El texto del cual extraer las entidades.

    Return:
        Un diccionario con las entidades extraídas.
    """
    ents = ner(text)
    persons, orgs = [], []
    for e in ents:
        label = e["entity_group"]
        if label == "PER":
            persons.append(e["word"])
        elif label == "ORG":
            orgs.append(e["word"])

    def delete_duplicates(items):
        """
        Elimina duplicados de la lista manteniendo el orden original. Tiene en cuenta si solo hay nombre o apellido.
        """
        out = []

        def norm(s):
            """
            Normaliza una cadena para comparaciones: minúsculas, sin '##' y sin espacios.
            """
            return (s or "").replace("##", "").strip().lower()

        for it in items:
            if not it:
                continue
            lw = norm(it)
            if not lw:
                continue

            # 1) Duplicado exacto -> saltar
            if any(lw == norm(x) for x in out):
                continue

            # 2) Si 'it' está contenido en algo ya guardado (más largo), lo ignoramos
            contained_idx = next((i for i, x in enumerate(out) if lw in norm(x) and len(x) >= len(it)), None)
            if contained_idx is not None:
                continue

            # 3) Si hay elementos guardados que son substring de 'it', los sustituimos/quitamos
            shorter_idxs = [i for i, x in enumerate(out) if norm(x) in lw and len(it) > len(x)]
            if shorter_idxs:
                first = shorter_idxs[0]
                out[first] = it  # reemplazo en sitio mantiene la posición
                # eliminar otras formas cortas (si hubiera varias)
                for i in reversed(shorter_idxs[1:]):
                    del out[i]
                continue

            # 4) Caso normal: añadir al final
            out.append(it)
        return out

    return {
        "persons": delete_duplicates(persons),
        "organizations": delete_duplicates(orgs),
    }



def _os_base_url():
    """
    Devuelve la URL base para el cliente de OpenSanctions.
    """
    return os.getenv("OPENSANCTIONS_CLIENT_URL", "http://app-1:8000")



def query_opensanctions(name, dataset="default", limit=1, timeout=5.0):
    """
    Consulta una sola entidad en OpenSanctions.

    Conditions:
        - El nombre de la entidad a consultar no debe estar vacío.
        - El conjunto de datos debe ser válido.

    Params:
        names: Lista de nombres a consultar.
        dataset: El conjunto de datos a consultar.
        limit: El número máximo de resultados a devolver.
        timeout: Tiempo máximo de espera para la consulta.

    Return:
        Un diccionario con los resultados de la consulta.

    """
    base = _os_base_url()
    params = {"q": name, "limit": limit}

    url = f"{base}/search/{dataset}"
    try:
        with httpx.Client(timeout=timeout) as cx:
            r = cx.get(url, params=params)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        return {"warning": f"OpenSanctions no disponible para '{name}': {e}", "results": []}



async def query_opensanctions_many(names, dataset="default", limit=1, timeout=5.0, max_concurrency=8):
    """
    Consulta varias entidades en paralelo. 

    Conditions:
        - La lista de nombres no debe estar vacía.
        - El conjunto de datos debe ser válido.

    Params:
        names: Lista de nombres a consultar.
        dataset: El conjunto de datos a consultar.
        limit: El número máximo de resultados a devolver.
        timeout: Tiempo máximo de espera para la consulta.

    Return:
        Un diccionario con los resultados de la consulta.
    """
    base = _os_base_url()
    params_common = {}
    url = f"{base}/search/{dataset}"

    # pequeño semáforo para limitar concurrencia
    sem = asyncio.Semaphore(max_concurrency)

    async def _one(session, name):
        params = {"q": name, "limit": limit, **params_common}
        try:
            async with sem:
                r = await session.get(url, params=params, timeout=timeout)
                r.raise_for_status()
                return name, r.json()
        except Exception as e:
            return name, {"warning": f"Error '{name}': {e}", "results": []}

    results = {}
    async with httpx.AsyncClient() as session:
        tasks = [_one(session, n) for n in names]
        for coro in asyncio.as_completed(tasks):
            name, data = await coro
            results[name] = data
    return results
