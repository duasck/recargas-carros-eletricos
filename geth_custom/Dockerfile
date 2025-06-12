# Usar a imagem oficial do Geth como base
FROM ethereum/client-go:v1.13.14

# A imagem é baseada em Alpine, então usamos o gerenciador de pacotes 'apk'
# Instala 'curl' (para debug manual, se necessário) e 'netcat-openbsd' para a healthcheck.
RUN apk update && apk add --no-cache curl netcat-openbsd
