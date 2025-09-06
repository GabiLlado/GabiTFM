import json, os, httpx, asyncio
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore, PineconeEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate




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



def extract_entities(ner, text):
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
    persons, orgs, misc = [], [], []
    for e in ents:
        label = e["entity_group"]
        if label == "PER":
            persons.append(e["word"])
        elif label == "ORG":
            orgs.append(e["word"])
        elif label == "MISC":
            misc.append(e["word"])

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
        "misc": delete_duplicates(misc),
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

mapping_sanciones = {
    "crime": "Delito",
    "crime.fraud": "Fraude",
    "crime.cyber": "Ciberdelincuencia",
    "crime.fin": "Delitos financieros",
    "crime.env": "Violaciones ambientales",
    "crime.theft": "Robo",
    "crime.war": "Crímenes de guerra",
    "crime.boss": "Liderazgo criminal",
    "crime.terror": "Terrorismo",
    "crime.traffick": "Trata de personas",
    "crime.traffick.drug": "Tráfico de drogas",
    "crime.traffick.human": "Trata de personas",
    "forced.labor": "Trabajo forzoso",
    "asset.frozen": "Activo congelado",
    "wanted": "Buscado",
    "corp.offshore": "Costa afuera",
    "corp.shell": "Compañía fantasma",
    "corp.public": "Empresa que cotiza en bolsa",
    "corp.disqual": "Descalificado",
    "gov": "Gobierno",
    "gov.national": "Gobierno nacional",
    "gov.state": "Gobierno estatal",
    "gov.muni": "Gobierno municipal",
    "gov.soe": "Empresa estatal",
    "gov.igo": "Organización intergubernamental",
    "gov.head": "Jefe de gobierno o de estado",
    "gov.admin": "Servicio civil",
    "gov.executive": "Rama ejecutiva del gobierno",
    "gov.legislative": "Rama legislativa del gobierno",
    "gov.judicial": "Rama judicial del gobierno",
    "gov.security": "Servicios de seguridad",
    "gov.financial": "La banca central y la integridad financiera",
    "gov.religion": "Liderazgo religioso",
    "fin": "Servicios financieros",
    "fin.bank": "Banco",
    "fin.fund": "Financiar",
    "fin.adivsor": "Asesor financiero",
    "mare.detained": "Detención marítima",
    "mare.shadow": "Flota de las sombras",
    "mare.sts": "Transferencia de barco a barco",
    "reg.action": "Acción del regulador",
    "reg.warn": "Advertencia del regulador",
    "role.pep": "Político",
    "role.pol": "No PEP",
    "role.rca": "Asociado cercano",
    "role.judge": "Juez",
    "role.civil": "Funcionario público",
    "role.diplo": "Diplomático",
    "role.lawyer": "Abogado",
    "role.acct": "Contador",
    "role.spy": "Espía",
    "role.oligarch": "Oligarca",
    "role.journo": "Periodista",
    "role.act": "Activista",
    "role.lobby": "Cabildero",
    "pol.party": "Partido político",
    "pol.union": "Unión",
    "rel": "Religión",
    "mil": "Militar",
    "sanction": "Entidad sancionada",
    "sanction.linked": "Entidad vinculada a sanciones",
    "sanction.counter": "Entidad contrasancionada",
    "export.control": "Exportación controlada",
    "export.risk": "Riesgo comercial",
    "debarment": "Entidad inhabilitada",
    "poi": "Persona de interés"
}

def summarize_entity_with_llm(llm, name, os_json, language="es"):
    """
    Resume con un LLM la info clave de un resultado de OpenSanctions.

    Params:
        llm: instancia de ChatOpenAI (LangChain)
        name: nombre consultado
        os_json: dict con el JSON devuelto por OpenSanctions para ese nombre
        language: 'es' o 'en'

    Return:
        str con el resumen
    """
    # Tomamos el primer resultado si existe; si no, resumimos el payload entero (incluyendo warnings)
    # Esto evita respuestas vacías si OS no devuelve coincidencias.
    if isinstance(os_json, dict) and "results" in os_json and os_json["results"]:
        payload = os_json["results"][0]
    else:
        payload = os_json

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Eres un analista que quiere buscar criminales o gente relacionada con ellos. "
         "Redacta un resumen breve, fiel y útil. "
         "Sé neutral; si faltan datos, dilo. No inventes."),
        ("user",
         "Idioma: {language}\n"
         "Entidad consultada: {name}\n\n"
         "Diccionario de referencia de etiquetas (para interpretar sanciones, generalmente en el campo 'topics'):\n{tag_ref}\n\n"
         "Datos (JSON):\n{data}\n\n"
         "Instrucciones de formato:\n"
         "Debes generar un resumen breve y claro con la información más relevante del JSON proporcionado, que contenga, si está disponible:"
         "el nombre completo de la entidad, nacionalidad, ocupación, si está sancionado (target=True) o no (target=False o no existe campo)"
         "y qué tipo de sanción tiene (suele estar en el campo topics). También otra información que consideres relevante\n")
    ])
    chain = prompt | llm
    try:
        res = chain.invoke({
            "language": language,
            "name": name,
            "tag_ref": json.dumps(mapping_sanciones, ensure_ascii=False, indent=2), # convierto el diccionario a json porque el llm no lee objetos python, solo texto
            "data": payload if isinstance(payload, str) else str(payload)
        })
        return getattr(res, "content", str(res))
    except Exception as e:
        return f"No se pudo generar el resumen para '{name}': {e}"


# --------------------------------------------------------------------------------------------------------------------------------------
# Pruebas
def select_os_match_llm(llm, query_name: str, os_json: dict, context_text: str = "", max_candidates: int = 8):
    """
    Pide al LLM que elija el mejor candidato de OpenSanctions para 'query_name',
    usando el contexto (query/answer RAG). Devuelve el dict completo del candidato elegido. Si ninguno encaja al 100%, di que no hay ninguno.
    """
    if not isinstance(os_json, dict) or not os_json.get("results"):
        return None
    cands = os_json["results"][:max_candidates]

    # Reducimos cada candidato a campos útiles para no gastar tokens
    compact = []
    for r in cands:
        compact.append(r)

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "Eres un analista de cumplimiento. Debes seleccionar el candidato de OpenSanctions "
         "que mejor corresponde a la entidad consultada. Puedes usar razonamiento personal solo cuando el contexto no sea suficiente."),
        ("user",
         "Entidad buscada: {name}\n\n"
         "Contexto (texto de apoyo):\n{ctx}\n\n"
         "Candidatos (JSON):\n{cands}\n\n"
         "Instrucciones:\n"
         "- Devuelve únicamente un JSON con esta forma exacta:\n"
         '  {{"id": "<ID_ELEGIDO>" , "reason": "<por_qué>"}}\n'
         "- Si ninguno cuadra, devuelve: {{\"id\": \"NONE\", \"reason\": \"...\"}}\n")
    ])

    res = (prompt | llm).invoke({
        "name": query_name,
        "ctx": (context_text or "")[:4000],  # recorte por seguridad
        "cands": json.dumps(compact, ensure_ascii=False)
    })
    text = getattr(res, "content", "").strip()

    # Parse robusto
    try:
        data = json.loads(text)
        chosen_id = data.get("id")
    except Exception:
        chosen_id = None

    if not chosen_id or chosen_id == "NONE":
        return None

    # Devuelve el candidato completo original (no el compacto), para poder resumirlo luego
    for r in cands:
        if r.get("id") == chosen_id:
            return r
    return None