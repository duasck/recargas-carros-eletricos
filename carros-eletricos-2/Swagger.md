# Visualizando a Documentação da API com Swagger UI

Este guia mostra como visualizar a documentação OpenAPI do sistema de carregamento de veículos elétricos usando o Swagger UI.

## Passo a Passo

### 1. Clone o repositório do Swagger UI

```bash
git clone https://github.com/swagger-api/swagger-ui.git
```

### 2. Acesse a pasta do Swagger UI

```bash
cd swagger-ui
```

### 3. Copie o arquivo `api_documentation.yaml` para a pasta `dist`

Coloque o arquivo [`api_documentation.yaml`](api_documentation.yaml) do seu projeto na pasta `swagger-ui/dist`.

### 4. Edite o arquivo `dist/index.html`

Abra o arquivo `swagger-ui/dist/index.html` em um editor de texto e altere a configuração da URL para apontar para o seu arquivo YAML local. Substitua a configuração do SwaggerUIBundle por:

```html
<script>
window.onload = function() {
  const ui = SwaggerUIBundle({
    url: "api_documentation.yaml",
    dom_id: '#swagger-ui',
    presets: [SwaggerUIBundle.presets.apis]
  });
};
</script>
```

### 5. Inicie um servidor HTTP local

Na pasta `swagger-ui/dist`, execute:

```bash
python -m http.server 8080
```

### 6. Acesse a documentação no navegador

Abra [http://localhost:8080](http://localhost:8080) no seu navegador. Você verá a documentação interativa da API baseada no arquivo [`api_documentation.yaml`](api_documentation.yaml).

---

**Dica:** Sempre que atualizar o arquivo [`api_documentation.yaml`](api_documentation.yaml), recarregue a página para ver as mudanças refletidas na interface do Swagger UI.