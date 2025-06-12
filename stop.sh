#!/bin/bash

echo "--- Parando e removendo todos os contêineres... ---"
docker compose -f docker-compose.servers.yml -f docker-compose.cars.yml down --remove-orphans
echo "--- Sistema parado. ---"