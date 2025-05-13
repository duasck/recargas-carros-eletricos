FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Não expor portas aqui, pois o docker-compose gerencia isso
CMD ["python", "-u", "server_a.py"]  # Alterado para um único comando (ajustado por serviço no docker-compose)