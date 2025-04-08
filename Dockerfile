FROM python:3.9-slim

# Cria e define o diretório de trabalho
WORKDIR /app

# Copia todos os arquivos para o container
COPY . .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Garante permissões adequadas
RUN chmod +x /app/*.py

# Define o usuário
USER 1000

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1