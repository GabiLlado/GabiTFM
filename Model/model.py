import json, argparse, asyncio
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnableLambda
from transformers import pipeline
from utils import model_ini, retrieve_docs, format_docs, extract_entities, query_opensanctions_many, summarize_entity_with_llm, select_os_match_llm


parser = argparse.ArgumentParser(description="Ejecuta una consulta RAG + OpenSanctions")
parser.add_argument("--query", required=True, help="Pregunta a realizar al modelo")
parser.add_argument("--numdocs", default=5, type=int, help="Número de documentos a recuperar de Pinecone")
args = parser.parse_args()

# Inicializo el modelo
llm = model_ini()

# Recupero los documentos de Pinecone
retriever = retrieve_docs(num_docs=args.numdocs)

# Defino un prompt con el contexto, poniendo al bot en situación y haciendo la pregunta. Esto es una plantilla.
prompt = ChatPromptTemplate.from_messages([
    ("system", "Responde solo con el contexto. Si falta info, dilo, no inventes. "
    "Menciona personas y entidades relevantes con nombre completo, si aparece."),
    ("user", "Pregunta: {question}\n\nContexto:\n{context}")
])

# Pipeline para el RAG
rag = (
    RunnableParallel(
        context=retriever | RunnableLambda(format_docs),
        question=lambda x: x
    )
    | prompt
    | llm
)


# Modelo multilingüe (incluye español) y agrega tokens contiguos automáticamente
ner = pipeline(
    task="token-classification",
    model="mrm8488/bert-spanish-cased-finetuned-ner",
    aggregation_strategy="simple"
)

# Aplico el RAG a la query, extraigo la respuesta y le aplico NER
result = rag.invoke(args.query)
answer_text = getattr(result, "content", str(result))
entities = extract_entities(ner, answer_text)

print("\n=== Respuesta del LLM ===")
print(answer_text)

print("\n=== Entidades (solo PERSON, ORG y MISC) ===")
print(json.dumps(entities, ensure_ascii=False, indent=2))

# Consultar en OpenSanctions tanto entidades como personas
persons = entities.get("persons", [])
orgs = entities.get("organizations", [])
misc = entities.get("misc", [])

# Realizo consultas en personas y organizaciones
all_entities = persons + orgs + misc
if all_entities:
    try:
        os_results = asyncio.run(
            query_opensanctions_many(
                all_entities,
                dataset="default",
                limit=5,
                timeout=5.0,
                max_concurrency=8,
            )
        )
        decision_context = f"Pregunta del usuario: {args.query}\nRespuesta RAG: {answer_text}"

        # model.py (sustituye el bloque que imprime resultados OS)
        print("\nRESULTADOS OPENSANCTIONS")
        for name in all_entities:
            print(f"\n--- {name} ---")
            data = os_results.get(name, {})
            # print(json.dumps(data, ensure_ascii=False, indent=2))

            chosen = select_os_match_llm(llm, name, data, context_text=decision_context, max_candidates=8)

            if chosen:
                # Empaquetamos como si fuera una respuesta OS con 1 resultado, para reutilizar tu summarizer
                single = {"results": [chosen]}
                summary = summarize_entity_with_llm(llm, name, single, language="es")
                print(summary)
            else:
                print("Ningún candidato coincide suficientemente con el contexto.")


    except Exception as e:
        print(f"\nError consultando OpenSanctions: {e}")
else:
    print("\nNo se detectaron entidades PERSON/ORG en la respuesta del LLM")
