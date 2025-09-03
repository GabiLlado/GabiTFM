import os
import json
import httpx
import argparse
import asyncio
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnableLambda
from transformers import pipeline
from utils import model_ini, retrieve_docs, format_docs, extract_person_org, query_opensanctions, query_opensanctions_many


parser = argparse.ArgumentParser(description="Ejecuta una consulta RAG + OpenSanctions")
parser.add_argument("--query", required=True, help="Pregunta a realizar al modelo")
args = parser.parse_args()

# Inicializo el modelo
llm = model_ini()

# Recupero los documentos de Pinecone
retriever = retrieve_docs(num_docs=5)

# Defino un prompt con el contexto, poniendo al bot en situación y haciendo la pregunta. Esto es una plantilla.
prompt = ChatPromptTemplate.from_messages([
    ("system", "Responde solo con el contexto. Si falta info, dilo."),
    ("user", "Pregunta: {question}\n\nContexto:\n{context}")
])

# Construyo el pipeline para el RAG
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
entities = extract_person_org(ner, answer_text)

print("\n=== Respuesta del LLM ===")
print(answer_text)

print("\n=== Entidades (solo PERSON y ORG) ===")
print(json.dumps(entities, ensure_ascii=False, indent=2))

# Consultar en OpenSanctions tanto entidades como personas
persons = entities.get("persons", [])
orgs = entities.get("organizations", [])

# Realizo consultas en personas y organizaciones
all_entities = persons + orgs
if all_entities:
    try:
        os_results = asyncio.run(
            query_opensanctions_many(
                all_entities,
                dataset="default",
                limit=1,
                timeout=5.0,
                max_concurrency=8,
            )
        )
        print("\n=== Resultados OpenSanctions por entidad ===")
        for name in all_entities:
            print(f"\n--- {name} ---")
            print(json.dumps(os_results.get(name, {}), ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"\nError consultando OpenSanctions: {e}")
else:
    print("\nNo se detectaron entidades PERSON/ORG en la respuesta del LLM")
