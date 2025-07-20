# 1. Usar una imagen base oficial de Python
# Usamos la versión 3.11 que sabemos que es estable para nuestras dependencias
FROM python:3.11-slim

# 2. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 2.1 Actualizamos la lista de paquetes y luego instalamos ca-certificates
RUN apt-get update && apt-get install -y ca-certificates

# 3. Copiar el archivo de requerimientos primero, para aprovechar el caché de Docker
COPY requirements.txt .

# 4. Instalar las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar todo el código fuente de la aplicación al contenedor
COPY . .

# 6. Exponer el puerto en el que correrá la aplicación
EXPOSE 8050

# 7. Comando para ejecutar la aplicación cuando se inicie el contenedor
CMD ["python", "app.py"]