# RecargasCarrosEletricos

## Sobre o Projeto
Este projeto simula um sistema de gerenciamento de recargas para carros elétricos, utilizando uma arquitetura distribuída baseada em containers Docker. Ele inclui os seguintes componentes principais:

- **Nuvem**: Responsável por gerenciar os pontos de recarga e os clientes, além de calcular os pontos mais próximos e distribuir as solicitações.
- **Pontos de Recarga**: Simulam estações de recarga que podem ser reservadas, iniciar recargas e liberar veículos.
- **Clientes**: Simulam veículos que interagem com a nuvem para localizar e utilizar os pontos de recarga.

O sistema foi desenvolvido como parte de um trabalho prático para a disciplina de Concorrência e Conectividade, com foco em escalabilidade e simulação de cenários reais.

## Como rodar o projeto

### Pré-requisitos
Certifique-se de ter os seguintes softwares instalados:
- [Docker](https://www.docker.com/)
- [Python 3.9+](https://www.python.org/)
- [pip](https://pip.pypa.io/en/stable/)

### Passo 1 - Instalar dependências
Antes de começar, instale as dependências do projeto:
```bash
pip install -r requirements.txt
```

### Passo 2 - Gerar o arquivo `docker-compose-generated.yml`
Execute o script `generate_compose.py` para gerar o arquivo de configuração do Docker Compose:
```bash
python generate_compose.py
```
Por padrão, ele cria 10 pontos de recarga e 5 clientes. Para personalizar esses valores, use:
```bash
python generate_compose.py --pontos NUMERO_DE_PONTOS --clientes NUMERO_DE_CLIENTES
```

### Passo 3 - Subir os containers com Docker Compose
Inicie os containers gerados:
```bash
docker-compose -f docker-compose-generated.yml up
```

### Passo 4 - Executar manualmente um cliente
Para interagir manualmente com um cliente, siga os passos abaixo:
1. Liste os containers em execução:
   ```bash
   docker ps --format "{{.Names}}"
   ```
2. Escolha o nome do container do cliente que deseja controlar (por exemplo, `recargascarroseletricos-cliente_1-1`).
3. Execute o cliente no modo interativo:
   ```bash
   docker exec -it recargascarroseletricos-cliente_1-1 python ./cliente.py --modo 1
   ```

### Passo 5 - Rodar em outra máquina
Se desejar rodar o cliente em outra máquina, siga os passos abaixo:
1. Descubra o endereço IP da máquina onde os containers estão rodando:
   - **Windows**:
     ```bash
     ipconfig | findstr "IPv4"
     ```
   - **Linux/Mac**:
     ```bash
     ifconfig | grep "inet "
     ```
2. Altere a configuração no arquivo `config.py`, substituindo `"localhost"` pelo IP obtido.
3. Execute o cliente no modo interativo:
   ```bash
   python cliente.py --modo 1
   ```

### Observação
- Para parar os containers, use:
  ```bash
  docker-compose -f docker-compose-generated.yml down
  ```
- Certifique-se de que os arquivos `dados_clientes.json` e `dados_pontos.json` estão atualizados antes de iniciar o sistema.