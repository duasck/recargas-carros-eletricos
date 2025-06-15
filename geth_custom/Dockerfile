# Usa a imagem oficial do Geth como base
FROM ethereum/client-go:v1.13.14

# A imagem é baseada em Alpine
# Instala 'curl' (para debug manual, se necessário) e 'netcat-openbsd' para a healthcheck.
RUN apk update && apk add --no-cache curl netcat-openbsd
