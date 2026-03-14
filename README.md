# Downloader Copernicus

Projeto em Python para autenticar no Copernicus Data Space Ecosystem (CDSE), localizar um produto Sentinel pelo nome e baixar o arquivo `.zip` para uma pasta local.

O script atual foi preparado para um fluxo simples e direto: informar o nome da imagem no próprio código e salvar o download automaticamente na pasta `imagens/` do projeto.

## Funcionalidades

- Autenticação no CDSE com credenciais armazenadas em `.netrc`
- Busca exata do produto no catálogo OData pelo campo `Name`
- Fallback automático para nomes com sufixo `.SAFE`
- Download autenticado do produto em formato `.zip`
- Salvamento automático na pasta `imagens/`

## Estrutura do projeto

```text
downloadercopernicus/
|-- imagens/
|-- copernicus_downloader.py
|-- pixi.toml
|-- pixi.lock
|-- README.md
```

## Requisitos

- Windows 64-bit
- [Pixi](https://pixi.sh/latest/) instalado
- Conta ativa no Copernicus Data Space Ecosystem
- Arquivo `.netrc` configurado no diretório do usuário

Dependências atuais do projeto:

- Python `>=3.14.3,<3.15`
- `requests`

## Configuração de credenciais

O script lê as credenciais a partir de:

```text
C:\Users\{seu_usuario}\.netrc
```

Exemplo de estrutura esperada:

```text
machine https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token
login SEU_LOGIN
password SUA_SENHA
```

Observações:

- Não versione o arquivo `.netrc`
- Cada pessoa que for usar o projeto deve criar e configurar o seu próprio `.netrc`
- Mantenha as credenciais fora do código-fonte
- O script também tenta um fallback para `identity.dataspace.copernicus.eu`, caso necessário

Se o repositório for público, esse cuidado é obrigatório: as credenciais devem existir apenas no ambiente local de quem executa o projeto.

## Instalação

Clone o repositório e entre na pasta do projeto:

```powershell
git clone <URL_DO_REPOSITORIO>
cd downloadercopernicus
```

Crie o ambiente com Pixi:

```powershell
pixi install
```

## Como usar

Abra o arquivo [`copernicus_downloader.py`](./copernicus_downloader.py) e edite a constante `NOME_IMAGEM`:

```python
NOME_IMAGEM = "S2A_MSIL2A_20220503T130251_N0510_R095_T23KPS_20241129T025850"
```

Depois execute:

```powershell
pixi run python .\copernicus_downloader.py
```

Se preferir, também funciona com Python já disponível no sistema:

```powershell
python .\copernicus_downloader.py
```

## Saida esperada

Ao concluir com sucesso, o arquivo será salvo em:

```text
imagens/<NOME_DO_PRODUTO>.zip
```

Exemplo:

```text
imagens/S2A_MSIL2A_20220503T130251_N0510_R095_T23KPS_20241129T025850.SAFE.zip
```

## Como funciona

O fluxo implementado pelo script é:

1. Ler `login` e `password` do arquivo `.netrc`
2. Solicitar um `access_token` ao endpoint de autenticação do CDSE
3. Consultar o catálogo OData pelo nome exato do produto
4. Obter o `Id` do produto encontrado
5. Fazer o download autenticado do conteúdo
6. Salvar o arquivo na pasta `imagens/`

## Tratamento de erros

O script já possui mensagens e exceções para cenários comuns:

- `.netrc` ausente
- credenciais incompletas
- produto não encontrado
- produto offline
- falha na autenticação
- erro HTTP durante o download

## Roadmap

Melhorias previstas para as próximas versões:

- leitura de uma lista de produtos a partir de arquivo texto
- download em lote
- logs mais detalhados
- barra de progresso
- parametrização por linha de comando
- testes automatizados

## Referências

- [Copernicus Data Space Ecosystem](https://dataspace.copernicus.eu/)
- [Documentação de autenticação](https://documentation.dataspace.copernicus.eu/APIs/Token.html)
- [Documentação da OData API](https://documentation.dataspace.copernicus.eu/APIs/OData.html)