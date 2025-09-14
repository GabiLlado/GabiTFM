FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Copia el archivo de requisitos y los instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python - <<'PY'
from transformers import pipeline
pipeline(
    "token-classification",
    model="mrm8488/bert-spanish-cased-finetuned-ner",
    aggregation_strategy="simple"
)
PY

# Copio toda la carpeta en la carpeta /app del contenedor
# El acceso a la app se hará por medio del puerto 8080
COPY . /app
EXPOSE 8080 

# Mantener contenedor en ejecución y permitir la ejecución de comandos manuales
CMD ["tail", "-f", "/dev/null"]