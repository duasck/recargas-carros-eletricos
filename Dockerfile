# Use uma versão específica do Python para reprodutibilidade
FROM python:3.11-slim

# Instalar wget para healthcheck
RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho
WORKDIR /app

# Define variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
# Adiciona o local dos binários do solc ao PATH
ENV PATH="/root/.solcx/solc-v0.8.0:${PATH}"

# Copia apenas o requirements.txt primeiro para aproveitar o cache do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala o compilador solc usando o próprio py-solc-x
# Isso evita a necessidade de instalar nodejs/npm
RUN python -c "import solcx; solcx.install_solc('0.8.0')"

# Copia o resto do código do projeto
COPY . .

# Comando padrão
CMD ["python"]