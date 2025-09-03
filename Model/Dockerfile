FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Copia el archivo de requisitos y los instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copio toda la carpeta en la carpeta /app del contenedor
# El acceso a la app se hará por medio del puerto 8080
COPY . /app
EXPOSE 8080 

# Mantener contenedor en ejecución y permitir la ejecución de comandos manuales
CMD ["tail", "-f", "/dev/null"]