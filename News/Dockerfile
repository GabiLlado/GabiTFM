FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Copia el archivo de requisitos y los instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copio toda la carpeta en la carpeta /app del contenedor
COPY . /app

# Mantener contenedor en ejecución y permitir la ejecución de comandos manuales
CMD ["tail", "-f", "/dev/null"]