# RecargasCarrosEletricos
Primeiro MI de Concorrência e Conectividade 

## Como rodar o projeto

#### 1 - Criando o docker-compose-generated.yml
- ``` python generate_compose.py ```
Por padrão ele gera 10 pontos de recarga e 5 clientes. Para alterar essas quantidades use: ``` python generate_compose.py --pontos numero_de_pontos --clientes numero_de_clientes```

### 2 - Rodar de forma iterativa o docker 
```docker run -it 065e643c175c python cliente.py```
```docker run -it 1b19a6855956 python nuvem.py```
```docker run -it 4d5452364284 python ponto_recarga.py```

```docker run -it --rm --network minha_rede --name cliente 9646d94632da  python cliente.py ```
```docker run -it --rm --network minha_rede --name nuvem 3c47dbbfaf87 python nuvem.py```
```docker run -it --rm --network minha_rede --name ponto a6ba32f0c719 python ponto_recarga.py```

#### 3 - Rodando o Compose gerado
- ``` docker-compose -f docker-compose-generated.yml up```

#### 4 - Rodando manualmente 
- Execute os arquivos ``` cliente.py```, ``` nuvem.py```, ``` ponto_recarga.py``` em terminais separados
