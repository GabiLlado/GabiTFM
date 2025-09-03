# client/Dockerfile
# Usa una imagen base de Python
FROM python:3.9-slim-buster

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los archivos de requisitos y los instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia los scripts de consulta
COPY scripts_queries/ scripts_queries/

# Crea un directorio para los resultados de las consultas
RUN mkdir -p results_queries

# Mantener contenedor en ejecución y permitir la ejecución de comandos manuales
CMD ["tail", "-f", "/dev/null"]