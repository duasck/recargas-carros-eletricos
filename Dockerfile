# Usa a imagem oficial do Python
FROM python:latest

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia os arquivos para dentro do contêiner
COPY app /app

# Expõe portas necessárias
EXPOSE 5000 6001 6002 6003

# Comando padrão (definido pelo docker-compose)
CMD ["python", "/app/nuvem.py"]
