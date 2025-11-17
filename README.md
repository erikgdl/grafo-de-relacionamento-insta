# 🕵️‍♂️ Analisador de Relacionamentos do Instagram

Este projeto é um script em Python que realiza uma análise profunda nos seguidores de um perfil público do Instagram.

Ele foi desenvolvido para ir além de simplesmente "quem segue quem". O script coleta dados detalhados, os salva de forma organizada para análise de negócios (Excel) e gera uma visualização de dados (grafo) que categoriza os relacionamentos do perfil-alvo.

## ✨ Funcionalidades Principais

  * **Coleta de Seguidores e Seguindo:** Busca a lista completa de *todos* os seguidores e de *todas* as contas que o perfil-alvo segue.
  * **Coleta de Dados Detalhados:** Para cada seguidor, extrai informações públicas como biografia, e-mail comercial, telefone de contato, contagem de mídias, etc.
  * **Processamento Paralelo:** Utiliza **Multithreading** (`ThreadPoolExecutor`) para acelerar a coleta de dados detalhados, fazendo 5 requisições simultâneas de forma segura.
  * **Exportação para Excel:** Salva todos os dados detalhados dos seguidores em um arquivo `.xlsx` limpo e organizado.
  * **Visualização em Grafo:** Gera e salva uma imagem `.png` de um grafo de relacionamentos, categorizando visualmente os usuários em três colunas:
    1.  **Só te Seguem:** Contas que seguem o alvo, mas o alvo não segue de volta.
    2.  **Mutuais:** Contas que se seguem mutuamente.
    3.  **Você Segue:** Contas que o alvo segue, mas não o seguem de volta.

-----

## 🛠️ Como Funciona (A Lógica)

Este script **não** usa `Selenium` ou *scraping* de HTML, que são métodos lentos e instáveis.

Em vez disso, ele simula um navegador logado (`requests.Session`) e consome a **API GraphQL interna** do Instagram. Isso é feito "enganando" o Instagram ao enviar os *cookies* de sessão (`sessionid` e `csrftoken`) de uma sessão de navegador válida.

### O Fluxo de Execução

1.  **Autenticação:** O script carrega os cookies em uma `requests.Session`.
2.  **Identificação:** O usuário digita o `@` do perfil-alvo. O script usa a API `web_profile_info` para encontrar o `user_id` numérico desse perfil.
3.  **Coleta de Listas:** Usando o `user_id` e os `query_hash` corretos, o script chama a API `GraphQL` em loop para baixar a lista completa de **Seguidores** (`QUERY_HASH_FOLLOWERS`) e **Seguindo** (`QUERY_HASH_FOLLOWING`).
4.  **Processamento Paralelo:** O script então usa 5 "trabalhadores" (threads) para percorrer a lista de seguidores e buscar os detalhes de cada um (usando a API `web_profile_info` de novo).
5.  **Geração de Saídas:**
      * Os dados detalhados são salvos em um `.xlsx` usando `pandas`.
      * As listas de seguidores/seguindo são usadas pelo `networkx` para construir um grafo.
      * Um algoritmo de layout customizado (`organizar_em_pilhas`) é usado para posicionar os nós do grafo nas 3 colunas.
      * O `matplotlib` desenha e salva o grafo como um `.png`.

-----

## 📋 Pré-requisitos

Para rodar este script, você precisa do Python 3 e das seguintes bibliotecas. Elas podem ser instaladas com:

```bash
pip install -r requirements.txt
```

O arquivo `requirements.txt` deve conter:

```txt
requests
pandas
openpyxl
networkx
matplotlib
```

-----

## 🚀 Como Usar

1.  **Encontre seus Cookies:**

      * Faça login no `instagram.com` no seu navegador (Chrome, Edge, etc.).
      * Aperte **F12** (Ferramentas de Desenvolvedor).
      * Vá na aba **Application** (ou "Aplicativo").
      * No menu da esquerda, vá em **Cookies** -\> `https://www.instagram.com`.
      * Encontre e copie os valores (Cookie Value) para `sessionid` e `csrftoken`.

2.  **Configure o Script:**

      * Abra o arquivo `main.py`.
      * Cole seus valores nas variáveis `SESSIONID_VALUE` e `CSRFTOKEN_VALUE` (no topo do script).

3.  **Execute:**

      * Abra seu terminal na pasta do projeto.
      * Ative seu ambiente virtual (se tiver um).
      * Rode o script:

    <!-- end list -->

    ```bash
    python main.py
    ```

4.  **Interaja:**

      * O script vai pedir o `@` do perfil que você quer analisar.
      * Ex: `erikyff_`
      * Aguarde. O processo pode levar vários minutos, dependendo do número de seguidores.

-----

## 📂 Saídas (O que ele cria)

Ao final da execução, você terá dois novos arquivos na pasta:

1.  **`[perfil-alvo]_instagram_data.xlsx`:** Uma planilha Excel com os dados detalhados de todos os **seguidores** do perfil.
2.  **`[perfil-alvo]_detailed_graph.png`:** Uma imagem em alta resolução do grafo de relacionamentos, mostrando as 3 categorias (Mutuais, Só Seguem, Você Segue).

-----

## 🔬 Análise das Funções (`def`)

  * `get_user_data(username)`: Busca os dados JSON completos de um perfil. É a "mágica" que obtém os e-mails, biografias, etc.
  * `get_user_id_from_username(username)`: Uma função de ajuda que usa `get_user_data` para pegar apenas o ID do usuário.
  * `fetch_graphql_list(...)`: A função central de coleta. Ela é genérica e pode buscar tanto Seguidores quanto Seguindo, dependendo do `query_hash` e das chaves que recebe. É ela que lida com a paginação (o "scroll infinito").
  * `get_followers(...)` / `get_following(...)`: Funções "atalho" que chamam `fetch_graphql_list` com os parâmetros corretos para cada caso.
  * `process_follower(follower_data)`: A função que o "trabalhador" (thread) executa. Ela pega os dados de um único seguidor, trata os erros (como o `address_json`), e retorna um dicionário limpo.
  * `organizar_em_pilhas(...)`: O algoritmo de layout customizado. Ele usa matemática (`math.ceil`, `%`, `//`) para organizar uma lista de pessoas em várias sub-colunas, garantindo que o grafo fique legível e não um "nó de cabelo".
  * `draw_detailed_graph(...)`: A função que cria o grafo. Ela usa `networkx` para construir as relações (nós e arestas), usa `organizar_em_pilhas` para definir a posição (`pos`) de cada nó, e usa `matplotlib` para desenhar e salvar a imagem.
  * `save_to_excel(...)`: Uma função simples que usa `pandas` para converter a lista de dicionários `results` em um arquivo Excel.
  * `main()`: A função principal que orquestra todo o processo: pede o input, chama os coletores, inicia o `ThreadPoolExecutor` para os *workers*, e por fim chama as funções de salvar (Excel e Grafo).

-----

## ⚠️ Aviso Importante

Este script depende de *cookies* de sessão (`sessionid`) que **expiram**\!

Se o script parar de funcionar e mostrar erros como **`Erro 401`** (Unauthorized) ou **`Erro 429`** (Too Many Requests), é 99% provável que seu `sessionid` expirou.

**Para corrigir:** Simplesmente faça logout e login no Instagram pelo navegador, pegue os **novos** cookies e atualize as variáveis no script.