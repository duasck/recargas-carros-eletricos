#!/bin/bash

set -e

echo "--- Regenerando arquivos docker-compose ---"
python generate_compose.py 5

echo "--- Removendo contêineres antigos ---"
docker compose -f docker-compose.servers.yml -f docker-compose.cars.yml down --remove-orphans

echo "--- Subindo apenas o Geth ---"
docker compose -f docker-compose.servers.yml up --build -d geth

echo "--- Aguardando Geth estar pronto (healthcheck) ---"
until [ "$(docker inspect -f '{{.State.Health.Status}}' geth)" == "healthy" ]; do
    echo "⏳ Aguardando Geth..."
    sleep 3
done

# 🧠 Endereço do deployer (conforme keys.json)
DEPLOYER_ADDR="0x66B0CEEf72EB99842bE1F701198f5306b1A8f29f"

echo "--- Enviando 100 ETH para o deployer ($DEPLOYER_ADDR) ---"
docker exec geth sh -c "geth attach http://localhost:8545 --exec 'eth.sendTransaction({from: eth.accounts[0], to: \"$DEPLOYER_ADDR\", value: web3.toWei(100, \"ether\")})'"

echo "--- Enviando 100 ETH para os carros ---"
CAR_ADDRESSES=(
  "0x76d8950c9a4E4C7DD8531D7f736B028CaE4b4BED"
  "0x862a43935a6bb4609C48aA4f7220dDac40f4cFA4"
  "0x3D6B78B0A8fe9e663ad55714dB087320DA63e331"
  "0xDD3Fa2e1415D6f3E6150381890B0F034c569962f"
  "0x90Bc0742d504Aef8b090Ef936DB13a146F654fcF"
)

for addr in "${CAR_ADDRESSES[@]}"; do
  echo "⛽ Enviando 100 ETH para $addr"
  docker exec geth sh -c "geth attach http://localhost:8545 --exec 'eth.sendTransaction({from: eth.accounts[0], to: \"$addr\", value: web3.toWei(100, \"ether\")})'"
done


echo "--- Subindo o restante dos serviços (incluindo deploy) ---"
docker compose -f docker-compose.servers.yml up --build -d

echo "--- Aguardando deploy do contrato ---"
docker compose -f docker-compose.servers.yml logs -f contract_deploy

echo "--- Iniciando carros ---"
docker compose -f docker-compose.cars.yml up --build

echo "--- ✅ Sistema iniciado com sucesso! ---"
