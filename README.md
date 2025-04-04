# RecargasCarrosEletricos
Primeiro MI de Concorrência e Conectividade 



## Como rodar o projeto

#### 1 - No terminal 
- ``` python random_info.py ```

#### 2 - Edite o docker-composer.yml
- ``` environment: NUM_PONTOS=N  (Número desejado de pontos)```
- ```NUM_CLIENTES=N  (Número desejado de clientes) ```
python generate_compose.py --pontos 15 --clientes 8
#### 3 - Construa e inicie os containers
- ``` docker-compose build```
- ```docker-compose up -d --scale ponto=N --scale cliente=N```
