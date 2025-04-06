# RecargasCarrosEletricos
Primeiro MI de Concorrência e Conectividade 

## Como rodar o projeto

#### 1 - Criando o docker-compose-generated.yml
- ``` python generate_compose.py ```
Por padrão ele gera 10 pontos de recarga e 5 clientes. Para alterar essas quantidades use: ``` python generate_compose.py --pontos numero_de_pontos --clientes numero_de_clientes```

#### 2 - Rodando o Compose gerado
- ``` docker-compose -f docker-compose-generated.yml up```

#### 3 - Rodando manualmente 
Execute os comandos 

- ``` docker ps --format "{{.Names}}" ```
- ``` docker exec -it recargascarroseletricos-cliente_1-1 python ./cliente.py --modo 1 ``` 

Escolha o nome da instancia que quer controlar nesse exemplo é o recargascarroseletricos-cliente_1-1



