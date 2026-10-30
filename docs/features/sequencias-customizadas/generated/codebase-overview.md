# deciframe — Pesquisa do Código Atual

**Data:** 2026-10-30  
**Repositório:** `/Users/vtex-ramon/workspaces/devia/ciframe`  
**Branch:** `master`  
**HEAD:** `fb970019d51a83e160477c115bf548684b567c53` — `Update 00-enunciado.md` (2026-10-17)  
**Árvore de trabalho:** limpa  
**Histórico:** 247 commits; primeiro commit `a1e82ab` (2014-03-21, “Initial commit of a Python Flask App Engine sample.”)

## Resumo de Alto Nível

deciframe é uma aplicação Flask que carrega um catálogo de 67.585 músicas de `data/top/dataset_final.csv` para a memória do processo no momento do import e serve respostas JSON a partir desse estado em memória; não há banco de dados. O backend é um único `main.py` mais um objeto de valor `Musica` em `musica.py`, com endpoints para busca textual, consulta por gênero/acorde e consultas de “músicas similares” por conjunto de acordes, por ID de música ou por sequência famosa de acordes. O frontend é uma aplicação de página única em AngularJS 1.4.9 + jQuery sob `static/`, carregada de CDNs sem etapa de build, usando cinco rotas hash: home, busca por acordes, busca por música, busca por sequência e sobre. A implantação em runtime é uma única imagem Docker (`python:3.9-slim`) executando gunicorn na porta 8080; `python main.py` local executa o servidor de desenvolvimento do Flask na porta 5000. Um conjunto separado de scripts Python 2, R, shell e Java em `scripts/` e `data/top/` documenta como o CSV e os conjuntos de dados auxiliares foram raspados e transformados offline; esses scripts não são importados pela aplicação em execução.

---

## 1. Runtime e Implantação

| Área | Estado atual | Referência |
|---|---|---|
| Imagem base do contêiner | `python:3.9-slim` | `Dockerfile:1` |
| Diretório de trabalho | `/app` | `Dockerfile:3` |
| Dependências | `Flask==3.1.3`, `gunicorn==23.0.0` | `requirements.txt:4-5` |
| Instalação | `pip install --no-cache-dir -r requirements.txt` | `Dockerfile:5-6` |
| Cópia | Repositório inteiro copiado para `/app` | `Dockerfile:8` |
| Porta exposta | `8080` | `Dockerfile:10` |
| Comando do contêiner | `gunicorn --bind 0.0.0.0:8080 main:app` | `Dockerfile:12` |
| Desenvolvimento local | `python main.py` inicia o Flask com `debug=True` na porta padrão 5000 | `main.py:279-280`, `README.md:22-31` |
| Execução Docker | `docker build -t ciframe .` e depois `docker run -p 8080:8080 ciframe` | `README.md:13-20` |
| Ignorado na imagem | `.git`, `.venv`, `__pycache__`, `*.pyc` | `.dockerignore:1-4` |
| Ignorado no git | `static/assets/vendor`, `.venv`, `*.pyc`, `__pycache__/` | `.gitignore:1-4` |

Não há driver de banco de dados, ORM, migração ou camada de persistência no conjunto de dependências de runtime. O estado da aplicação é reconstruído a partir do CSV a cada início de processo.

O repositório não contém diretório de testes, configuração de executor de testes nem arquivo de configuração de CI.

---

## 2. Backend

### 2.1 Ponto de entrada e inicialização da aplicação

`main.py` é o ponto de entrada do Flask. Ele importa `Flask`, `request`, `json`, `sys`, `OrderedDict`, `unicodedata` e tudo de `musica.py` (`main.py:1-7`). A aplicação Flask é criada em `main.py:9`.

No momento do import, antes de qualquer requisição ser servida, `main.py` executa toda a carga do conjunto de dados (`main.py:37-98`):

1. Os índices de coluna são fixados como constantes (`main.py:25-34`):
   - `ARTISTA_ID = 0`
   - `MUSICA_ID = 1`
   - `ARTISTA = 2`
   - `MUSICA = 3`
   - `GENERO = 4`
   - `POPULARIDADE = 5`
   - `TOM = 6`
   - `SEQ_FAMOSA = 7`
   - `CIFRA = 8`
2. O tamanho da página é fixado em `TAM_PAGINA = 100` (`main.py:35`).
3. Os contêineres globais são inicializados (`main.py:37-47`):
   - `genero_musicas` — nome do gênero → lista de objetos `Musica`
   - `generos` — conjunto de nomes de gêneros
   - `acordes` — conjunto de tokens de acordes
   - `sequencias` — seis chaves de sequências famosas mapeadas para IDs inteiros (`main.py:40-45`)
   - `musicas_dict` — ID único de música → objeto `Musica`
4. O CSV é aberto e sua primeira linha é descartada com `f.readline()` (`main.py:49-50`).
5. Para cada linha restante (`main.py:52-85`):
   - `line.replace('"', '').replace('NA', '')[:-1]` remove aspas duplas, remove toda ocorrência da substring `NA` e descarta o último caractere (`main.py:53`).
   - A linha é dividida por vírgulas em nove campos (`main.py:55`).
   - A popularidade é convertida com `int(musica[POPULARIDADE].replace('.', ''))` (`main.py:56`).
   - O campo de acordes é dividido por `;` e passado por `limpa_cifra`, ou definido como `[]` quando vazio (`main.py:58-61`).
   - O campo de sequência famosa é dividido por `;` (`main.py:63`).
   - O gênero é adicionado ao conjunto `generos` (`main.py:66`).
   - Um objeto `Musica` é criado e armazenado sob `musica_obj.id_unico_musica` (`main.py:69-74`).
   - Cada acorde em `musica_obj.acordes` é adicionado ao conjunto global `acordes` (`main.py:77-78`).
   - A música é anexada a `genero_musicas[genero]` (`main.py:82-85`).
6. `musicas` é um `OrderedDict` de `musicas_dict` ordenado por `popularidade` decrescente (`main.py:88-89`).
7. `generos` é convertido de conjunto para lista (`main.py:92`).
8. A lista de músicas de cada gênero é ordenada por `popularidade` decrescente (`main.py:95-96`).
9. O arquivo é fechado (`main.py:98`).

Como a carga acontece no import do módulo, editar o CSV exige reiniciar o processo; nenhum caminho de requisição relê o arquivo.

### 2.2 Auxiliar de parsing do CSV

`limpa_cifra(raw_cifra)` (`main.py:11-23`) converte uma lista de segmentos brutos do campo de acordes em uma lista plana de tokens de acordes:

- Segmentos vazios ou somente com espaços são ignorados (`main.py:14`).
- Se um segmento contém `|` (tablatura), ele pega o texto antes do primeiro `|`, divide por espaços e mantém o primeiro token (`main.py:16-18`).
- Caso contrário, divide o segmento por espaços e acrescenta todos os tokens (`main.py:19-22`).

O resultado é armazenado como `Musica.cifra`; `Musica.acordes` é o conjunto deduplicado desses tokens convertido de volta para lista (`musica.py:16-17`).

### 2.3 Modelo de domínio

`musica.py:1-25` define uma classe:

| Atributo | Origem / construção | Referência |
|---|---|---|
| `id_artista` | argumento do construtor | `musica.py:7` |
| `nome_artista` | argumento do construtor | `musica.py:8` |
| `id_musica` | argumento do construtor | `musica.py:10` |
| `nome_musica` | argumento do construtor | `musica.py:11` |
| `genero` | argumento do construtor | `musica.py:13` |
| `popularidade` | argumento do construtor | `musica.py:14` |
| `tom` | argumento do construtor | `musica.py:15` |
| `cifra` | argumento do construtor | `musica.py:16` |
| `acordes` | `list(set(cifra))` | `musica.py:17` |
| `seqs_famosas` | argumento do construtor | `musica.py:18` |
| `id_unico_musica` | `'%s_%s' % (id_artista, id_musica)` | `musica.py:20` |
| `url` | `http://www.cifraclub.com.br/<id_artista>/<id_musica>` | `musica.py:22` |
| `__str__` | `'<id_unico_musica>,<genero>,<popularidade>'` | `musica.py:24-25` |

### 2.4 Superfície HTTP

Todas as rotas são definidas em `main.py`. As respostas são produzidas com `json.dumps(...)` e retornadas como strings Python, então o Flask as serve com `Content-Type: text/html; charset=utf-8` em vez de `application/json`.

| Rota | Handler | Entradas | Comportamento atual | Referência |
|---|---|---|---|---|
| `GET /` | `index` | nenhuma | Envia `static/index.html` via `app.send_static_file` | `main.py:101-103` |
| `GET /<path:path>` | `static_proxy` | qualquer caminho | Envia o arquivo correspondente do diretório `static/` do Flask | `main.py:109-112` |
| `GET /search` | `busca` | `key` (obrigatório), `generos` (opcional, separado por vírgulas), `pagina` (opcional, padrão `'1'`) | Busca por tokens insensível a acentos sobre artista + título da música, opcionalmente filtrada por gênero; retorna uma página de 100 itens | `main.py:114-142` |
| `GET /musicas` | `get_musicas` | nenhuma | Retorna todo `Musica.__dict__` em ordem decrescente de popularidade | `main.py:154-156` |
| `GET /generos` | `get_generos` | nenhuma | Retorna a lista `generos` | `main.py:158-160` |
| `GET /acordes` | `get_acordes` | nenhuma | Retorna o conjunto `acordes` como lista | `main.py:162-164` |
| `GET /musica/<m_id>/` | `get_musica` | `m_id` = `id_unico_musica` | Retorna um `Musica.__dict__` | `main.py:166-168` |
| `GET /similares` | `get_similares` | `acordes`, `id_unico_musica`, `sequencia`, `generos`, `pagina` | Retorna músicas similares por conjunto de acordes, por música de origem ou por sequência famosa; paginado em 100 | `main.py:170-201` |

#### Detalhes de `/search`

- `request.args.get('key')` é convertido para minúsculas e tem os acentos removidos, depois é dividido por espaços (`main.py:118-119`).
- Se `generos` estiver presente, é dividido por vírgulas; caso contrário, a lista completa `generos` é usada (`main.py:121-123`).
- As músicas candidatas vêm de `apply_filtro(...)` (`main.py:125`).
- Uma música só corresponde quando todo token da consulta aparece como token exato na lista de tokens, sem acentos e em minúsculas, de `"<artista> <título>"` (`main.py:128-131`).
- Cada resultado contém `id_unico_musica`, `id_artista`, `id_musica`, `nome_artista`, `nome_musica`, `genero` e `url` (`main.py:132-140`).
- A lista de resultados é paginada com `get_pagina(out, pagina_tag)` (`main.py:142`).

`remover_combinantes` normaliza com Unicode NFD e remove marcas combinantes (`main.py:145-147`).

#### Detalhes de `/musicas`

O handler retorna `[v.__dict__ for v in musicas.values()]` (`main.py:156`). A docstring acima dele descreve paginação com tamanho padrão de 100 (`main.py:149-153`), enquanto o handler em si retorna a lista completa e não lê um argumento `pagina`.

#### Detalhes de `/similares`

A rota lê cinco parâmetros de consulta (`main.py:173-176`):

- `acordes`
- `id_unico_musica`
- `sequencia`
- `pagina` (padrão `'1'`)
- `generos`

O tratamento de gênero espelha `/search`: ausência de `generos` significa todos os gêneros (`main.py:179-182`).

A origem dos acordes é selecionada nesta ordem (`main.py:184-197`):

1. Se `acordes` estiver presente, é dividido por vírgulas (`main.py:185-186`).
2. Senão, se `id_unico_musica` estiver presente, a música é procurada em `musicas` e sua lista `acordes` é usada (`main.py:187-189`).
3. Senão, se `sequencia` estiver presente, as vírgulas são removidas e a string resultante é procurada no dicionário `sequencias` (`main.py:190-197`).
   - Se encontrada, `get_similares_por_sequencia(id_seq, generos_key)` é chamada e paginada.
   - Se não encontrada, o handler retorna `json.dumps([])`.
4. Caso contrário, `get_similares(acordes, generos_key, id_musica_tag)` é chamada com a lista de acordes vazia (`main.py:199`).

Os modos `acordes` e `id_unico_musica` retornam objetos com os campos `diferenca` e `intersecao` (`main.py:246-258`). O modo `sequencia` retorna objetos sem esses campos (`main.py:210-220`).

#### Auxiliares de similaridade

`get_similares_por_sequencia(id_seq, generos_key)` (`main.py:203-223`):

- Filtra o catálogo por gênero usando `apply_filtro` (`main.py:205`).
- Mantém músicas em que `str(id_seq)` é um elemento de `musica.seqs_famosas` (`main.py:209`).
- Retorna `id_unico_musica`, `id_artista`, `id_musica`, `nome_artista`, `nome_musica`, `popularidade`, `acordes`, `genero` e `url` (`main.py:210-220`).

`get_similares(acordes, generos_key, id_musica=None)` (`main.py:230-263`):

- Filtra o catálogo por gênero (`main.py:233`).
- Ignora a música de origem quando `id_musica` corresponde (`main.py:238`).
- Calcula `inter = set(acordes) & set(musica.acordes)` e `diff = set(musica.acordes) - set(acordes)` (`main.py:240-241`).
- Mantém apenas músicas com interseção não vazia (`main.py:245`).
- Adiciona `diferenca` e `intersecao` como listas (`main.py:256-257`).
- Ordena com `key=lambda x: (len(x['diferenca']), -len(x['intersecao']))` (`main.py:263`). O comentário em `main.py:262` também menciona popularidade; a chave de ordenação real contém apenas o tamanho da diferença e o tamanho negativo da interseção.

`get_pagina(colecao, pagina_tag)` fatia de `(int(pagina_tag) - 1) * 100` até esse deslocamento mais 100 (`main.py:226-228`).

`apply_filtro(musicas, generos_key)` (`main.py:266-272`):

- Ignora a coleção `musicas` recebida.
- Itera `generos_key`, mantém apenas nomes presentes no conjunto global `generos` e concatena `genero_musicas[genero]` para cada um.
- A ordem retornada é, portanto, a ordem de `generos_key` e, dentro de cada gênero, a ordem decrescente de popularidade estabelecida na inicialização.

### 2.5 Convenções de resposta e comportamento transversal

- Todo handler de API retorna `json.dumps(...)` diretamente; nenhum usa `jsonify` (`main.py:142`, `156`, `160`, `164`, `168`, `197`, `201`).
- `@app.after_request` adiciona `Access-Control-Allow-Origin: *` a toda resposta (`main.py:274-277`).
- O proxy estático e a rota de índice servem arquivos do frontend a partir de `static/` (`main.py:101-112`).
- As seis sequências famosas são definidas em `main.py:40-45`:
  - `BmGDA` → `0`
  - `CGAmF` → `1`
  - `EmG` → `2`
  - `CA7DmG7` → `3`
  - `GmF` → `4`
  - `CC7FFm` → `5`

### 2.6 Fatos do conjunto de dados em memória

Medidos a partir do `data/top/dataset_final.csv` atual usando os mesmos passos de parsing de `main.py`:

| Fato | Valor |
|---|---|
| Tamanho do arquivo | 15 MB |
| Linhas físicas | 67.586 |
| Linha de cabeçalho | Nenhuma; a linha 1 é uma linha de dados (`14-bis,a-qualquer-tempo,...`) |
| Registros carregados em `musicas` | 67.585 (linha 1 descartada por `main.py:50`) |
| Chaves únicas de `id_unico_musica` | 67.585 |
| Gêneros no conjunto do backend | 52 |
| Tokens únicos de acordes em `acordes` | 6.653 |
| Registros com `CIFRA` vazio | 8.141 |
| Música mais popular | Guns N’ Roses — “Sweet Child O’ Mine”, popularidade `7.063.127` |
| Faixa de popularidade | `0` a `7.063.127` |
| Contagens da tag `SEQ_FAMOSA` | `0`: 199, `1`: 296, `2`: 4, `3`: 5, `4`: 7, `5`: 3 |
| Gênero ausente na lista do frontend | `R&B;` (armazenado com ponto e vírgula no final) |

A primeira linha de dados (`14-bis,a-qualquer-tempo`) não está em `musicas_dict`, então `/musica/14-bis_a-qualquer-tempo/` retorna um 500 `KeyError`; a linha seguinte (`14-bis_adoraveis-criaturas`) é carregada.

`generos` e `acordes` derivam de conjuntos Python, então a ordem de suas listas não é ordenada nem estável entre execuções. Uma resposta ao vivo de `/generos` começou com `['Punk Rock', 'Soft Rock', 'MPB', 'Rock', 'Sertanejo']`; uma resposta ao vivo de `/acordes` começou com `['E4/7(9)', 'A#7+/D', 'G7(4/9)', 'B(9)', 'A5+(9)', 'Db7(4)', 'Gbm6', 'G(b9)']`.

---

## 3. Frontend

### 3.1 Shell e dependências

`static/index.html` é o único shell HTML:

- `<html lang="pt" ng-app="deciframeApp">` (`static/index.html:2`).
- O body usa `ng-controller="MainController"` (`static/index.html:22`).
- Os metadados Open Graph apontam para `http://deciframe.com/` e `static/assets/img/deciframe.png` (`static/index.html:7-11`).
- O Google Analytics usa a propriedade `UA-85286010-1` (`static/index.html:25-32`).
- A view principal é `<div class="page" ng-view></div>` (`static/index.html:123`).
- O menu deslizante (`ng-show="showMenu"`) contém a descrição do projeto e os links da equipe (`static/index.html:90-121`).

Scripts externos e locais são carregados nesta ordem (`static/index.html:125-147`):

| Script | Versão/origem | Referência |
|---|---|---|
| jQuery | 1.11.3, Google CDN | `static/index.html:126` |
| Bootstrap JS | 3.3.6, MaxCDN | `static/index.html:128` |
| AngularJS | 1.4.9, cdnjs | `static/index.html:130` |
| angular-route | 1.4.9 | `static/index.html:131` |
| angular-animate | 1.4.9 | `static/index.html:132` |
| angular-ui-bootstrap | 2.1.4 | `static/index.html:133-134` |
| ngProgress | local `assets/js/ngprogress.js` | `static/index.html:136` |
| App | `assets/js/app.js` | `static/index.html:138` |
| Rotas | `assets/js/routes.js` | `static/index.html:139` |
| Controllers | `main.js`, `home.js`, `about.js`, `acordes.js`, `musica.js`, `sequencia.js` | `static/index.html:140-145` |
| Diretivas | `df-hex.js`, `df-esfinge.js` | `static/index.html:146-147` |

`static/assets/js/controllers/search.js` existe, mas não está incluído em `index.html`. `static/bower.json` declara `ng-material-floating-button` (`static/bower.json:23-25`), que `index.html` não carrega.

Os arquivos CSS são `static/assets/css/app.css` (652 linhas), `static/assets/css/icons.css` (36 linhas), Bootstrap 3.3.6 do MaxCDN e a fonte Google Varela Round (`static/index.html:13-19`). `app.css` define as classes de painel e cartão usadas pelos templates, incluindo `viewWindow-panel` (`static/assets/css/app.css:69-82`), `music-card`, `acorde-wrapper`, `vertical-panel`, `menu-container` e `esfinge`.

### 3.2 Módulo Angular e rotas

`static/assets/js/app.js:1-2` cria o módulo `deciframeApp` com as dependências `ngRoute`, `ngAnimate`, `ngProgress` e `ui.bootstrap`.

`app.js:3-5` declara uma constante `RESTAPI` com `url: 'http://localhost:5003'`; nenhum controller ou template referencia essa constante. Os controllers usam um `apiUrl = ""` local, produzindo requisições relativas para a mesma origem (`static/assets/js/controllers/acordes.js:91`, `musica.js:12`, `sequencia.js:72`).

`app.js:6-58` declara uma constante `GENEROS` contendo 51 strings de gênero. O conjunto de gêneros do backend contém 52 entradas; o valor extra do backend é `R&B;`.

`static/assets/js/routes.js:1-29` define:

| Rota | Template | Controller | Apelido do controller | Referência |
|---|---|---|---|---|
| `/` | `templates/home.html` | `HomeController` | nenhum | `routes.js:3-6` |
| `/poracordes` | `templates/acordes.html` | `AcordesController` | `Chords` | `routes.js:7-11` |
| `/pormusica` | `templates/musica.html` | `MusicaController` | `Musica` | `routes.js:12-16` |
| `/porsequencia` | `templates/sequencia.html` | `SequenciaController` | `Sequencia` | `routes.js:17-21` |
| `/sobre` | `templates/about.html` | `AboutController` | nenhum | `routes.js:22-25` |
| caso contrário | redireciona para `/` | — | — | `routes.js:26-28` |

### 3.3 Controllers

#### `MainController` — `static/assets/js/controllers/main.js:1-12`

- `$scope.showMenu = false` (`main.js:2`).
- `isActive(path)` testa `$route.current.regexp` contra um caminho (`main.js:3-8`).
- `toggleMenu()` inverte `showMenu` (`main.js:9-11`).
- O template usa `isActive('/')` para ocultar o logo na rota home (`static/index.html:40`).

#### `HomeController` — `static/assets/js/controllers/home.js:1-4`

Define `pageTitle = 'Home'` e `pageClass = 'page-home'`. O template home não renderiza nenhum dos dois valores.

#### `AboutController` — `static/assets/js/controllers/about.js:1-4`

Define `pageTitle = 'Sobre'` e `pageClass = 'page-about'`; `about.html:5` renderiza `{{pageTitle}}`.

#### `AcordesController` — `static/assets/js/controllers/acordes.js:1-125`

- Define sete grupos de acordes como arrays de objetos `{acorde, cor}` (`acordes.js:2-44`):
  - Grupo C: 6 entradas
  - Grupo D: 6 entradas
  - Grupo E: 3 entradas
  - Grupo F: 6 entradas
  - Grupo G: 6 entradas
  - Grupo A: 6 entradas
  - Grupo B: 3 entradas
  - Total: 36 botões de acordes.
- Insere os grupos em `vm.acordes` (`acordes.js:45-53`).
- Inicializa `vm.meusAcordes = []`, o estado de busca, `vm.generos = GENEROS`, `vm.meuGenero = ""` e uma instância de `ngProgress` (`acordes.js:54-61`).
- `addAcorde(acorde)` alterna o acorde em `vm.meusAcordes` e chama imediatamente `pesquisarPorAcordes()` (`acordes.js:63-71`).
- `temAcorde(acorde)` verifica a presença (`acordes.js:72-74`).
- `createChordsString(chords)` une nomes de acordes com vírgulas (`acordes.js:76-82`).
- `pesquisarPorAcordes()` (`acordes.js:84-115`):
  - Inicia o progresso e define o texto de fala quando há pelo menos um acorde selecionado.
  - Monta `similares?acordes=<acordes separados por vírgula>`.
  - Anexa `&generos=<gênero>` quando `vm.meuGenero` não está vazio.
  - Chama `$http.get(apiUrl.concat(searchString))`.
  - Armazena o array de resposta em `vm.musics`.
  - Não envia o parâmetro `pagina`, então o backend retorna a página 1.
- `goToLirics(music)` abre `music.url` em uma nova janela (`acordes.js:117-119`).
- `goToResults()` oculta o botão de contagem de resultados e anima a página até `#results` (`acordes.js:121-124`).

#### `MusicaController` — `static/assets/js/controllers/musica.js:1-80`

- Inicializa `vm.acordes = []`, `vm.minhaMusica = {}`, o estado de busca, `vm.generos = GENEROS`, `vm.meuGenero = ""` e uma instância de `ngProgress` (`musica.js:2-11`).
- `getMusicas(val)` chama `GET search?key=<val>` e retorna `response.data` para o typeahead (`musica.js:14-20`).
- `addAcorde` e `temAcorde` referenciam `vm.meusAcordes` (`musica.js:22-33`); este controller não inicializa `vm.meusAcordes`.
- `createChordsString` é definido (`musica.js:35-41`).
- `pesquisarPorMusica(musica)` (`musica.js:43-70`):
  - Usa a música selecionada ou o `vm.minhaMusica` existente.
  - Monta `similares?id_unico_musica=<id_unico_musica>`.
  - Anexa `&generos=<gênero>` quando selecionado.
  - Armazena o array de resposta em `vm.musics`.
  - Não envia o parâmetro `pagina`.
- `goToLirics` e `goToResults` espelham o controller de acordes (`musica.js:72-79`).

#### `SequenciaController` — `static/assets/js/controllers/sequencia.js:1-105`

- Define quatro objetos de sequência em JavaScript (`sequencia.js:2-31`):
  - `sequencia1`: `Bm, G, D, A`
  - `sequencia2`: `C, G, Am, F`
  - `sequencia3`: `Gm, F`
  - `sequencia4`: `C, C7, F, Fm`
- Insere-os em `vm.sequenciasFamosas` (`sequencia.js:32-37`).
- Inicializa o estado de busca, `vm.generos = GENEROS`, `vm.meuGenero = ""` e uma instância de `ngProgress` (`sequencia.js:38-45`).
- `temAcorde(acorde)` verifica a presença em `vm.minhaSequencia.acordes` quando presente (`sequencia.js:47-53`).
- `createChordsString` une nomes de acordes com vírgulas (`sequencia.js:55-61`).
- `pesquisarPorSequencia(sequencia)` (`sequencia.js:63-90`):
  - Usa a sequência passada ou o `vm.minhaSequencia` atual.
  - Monta `similares?sequencia=<acordes separados por vírgula>`.
  - Anexa `&generos=<gênero>` quando selecionado.
  - Armazena o array de resposta em `vm.musics`.
  - Não envia o parâmetro `pagina`.
- `limparPesquisa()` limpa a sequência selecionada e os resultados (`sequencia.js:92-95`).
- `goToLirics` e `goToResults` espelham os outros controllers (`sequencia.js:97-104`).

As quatro sequências do frontend correspondem aos IDs de backend `0`, `1`, `4` e `5`. O backend também reconhece `EmG` (ID `2`) e `CA7DmG7` (ID `3`), que não têm botão em `sequencia.html`.

#### `SearchController` — `static/assets/js/controllers/search.js:1-26`

Define um `SearchController` que insere um resultado fictício de “Californication” e chama `$http.get("")`; a atribuição real da resposta está comentada (`search.js:9-20`). O arquivo não é carregado por `index.html`.

### 3.4 Diretivas

| Diretiva | Restrição | Escopo isolado | Template | Referência |
|---|---|---|---|---|
| `dfHex` | elemento | `acorde: '@'`, `acordeColor: '@'`, `acordeChecked: '='`, `small: '='` | `templates/directives/df-hex.html` | `static/assets/js/directives/df-hex.js:1-12` |
| `dfEsfinge` | elemento | `dfAnimated: '='` | `templates/directives/df-esfinge.html` | `static/assets/js/directives/df-esfinge.js:1-9` |

`df-hex.html` renderiza um hexágono SVG cujo preenchimento é `#FFF` quando `acordeChecked` é verdadeiro e `acordeColor` caso contrário; a cor do rótulo do acorde muda para `#474747` quando marcado (`static/templates/directives/df-hex.html:1-9`).

`df-esfinge.html` é uma ilustração SVG de 326 linhas com classes CSS para `flyUpDown`, `flyShadow`, `rotateInUpLeft` e `rotateInUpRight`; a classe `animated` é aplicada condicionalmente a partir de `dfAnimated` (`static/templates/directives/df-esfinge.html:24-25`, `119`, `144`). O template home a usa em `static/templates/home.html:7`.

### 3.5 Templates e interação

#### Home — `static/templates/home.html:1-90`

- Renderiza a diretiva da esfinge e o logo SVG do deciframe (`home.html:6-54`).
- Três painéis de navegação apontam para `#/poracordes`, `#/pormusica` e `#/porsequencia` (`home.html:58-86`).
- Nenhuma requisição de API é feita na rota home.

#### Acordes — `static/templates/acordes.html:1-96`

- Renderiza a paleta de 36 acordes com `ng-repeat` aninhado sobre `Chords.acordes` (`acordes.html:6-8`).
- Cada hexágono chama `Chords.addAcorde(acordeon)` ao clicar (`acordes.html:7`).
- O dropdown de gênero usa `Chords.generos` e chama `Chords.pesquisarPorAcordes()` na mudança (`acordes.html:24-30`).
- Os acordes selecionados são renderizados a partir de `Chords.meusAcordes`; clicar em um o remove (`acordes.html:34`).
- Os cartões de resultado são divididos em dois grupos:
  - Músicas sem `diferenca` são mostradas como tocáveis (`acordes.html:40-59`, `ng-hide="music.diferenca.length"`).
  - Músicas com `diferenca` não vazio são mostradas em “Aprenda mais alguns acordes para tocar” com os acordes faltantes renderizados como hexágonos pequenos (`acordes.html:61-91`).
- Os resultados são ordenados no navegador com `orderBy:'-popularidade'` (`acordes.html:42`, `66`).

#### Música — `static/templates/musica.html:1-119`

- O campo de busca usa `uib-typeahead` com `Musica.getMusicas($viewValue)`, mínimo de 3 caracteres, debounce de 1000 ms e `Musica.pesquisarPorMusica(minhaMusica)` na seleção (`musica.html:8-18`).
- O dropdown de gênero chama `Musica.pesquisarPorMusica()` na mudança (`musica.html:34-40`).
- A música selecionada é destacada a partir de `Musica.minhaMusica` (`musica.html:46-62`).
- As músicas similares são renderizadas com a mesma divisão por `diferenca` da página de acordes (`musica.html:63-113`).
- Os resultados são ordenados no navegador com `orderBy:'-popularidade'` (`musica.html:64`, `88`).

#### Sequência — `static/templates/sequencia.html:1-63`

- Renderiza as quatro sequências definidas em JavaScript com `ng-repeat` sobre `Sequencia.sequenciasFamosas` (`sequencia.html:6-8`).
- Clicar em uma sequência chama `Sequencia.pesquisarPorSequencia(sequencia)` (`sequencia.html:6`).
- O dropdown de gênero chama `Sequencia.pesquisarPorSequencia()` na mudança (`sequencia.html:24-30`).
- Os acordes da sequência selecionada são renderizados a partir de `Sequencia.minhaSequencia.acordes`; clicar em um chama `Sequencia.limparPesquisa()` (`sequencia.html:33-36`).
- Os cartões de resultado usam `ng-repeat="music in Sequencia.musics | orderBy:'-popularidade'"` e `ng-hide="music.diferenca.length"` (`sequencia.html:41-43`). A resposta de sequência do backend não contém o campo `diferenca` (`main.py:210-220`).

#### Sobre — `static/templates/about.html:1-9`

Renderiza `{{pageTitle}}` dentro de um único painel; nenhum outro conteúdo está presente.

### 3.6 Contratos de requisição frontend/backend

| Ação do frontend | Requisição | Modo do backend | Campos da resposta usados pelo template |
|---|---|---|---|
| Busca na paleta de acordes | `GET similares?acordes=<acordes>[&generos=<gênero>]` | `get_similares` via `acordes` | `nome_musica`, `nome_artista`, `genero`, `popularidade`, `diferenca`, `url` |
| Typeahead de música | `GET search?key=<texto>` | `busca` | `id_unico_musica`, `nome_musica`, `nome_artista` |
| Similaridade por música | `GET similares?id_unico_musica=<id>[&generos=<gênero>]` | `get_similares` via `id_unico_musica` | `nome_musica`, `nome_artista`, `genero`, `popularidade`, `diferenca`, `url` |
| Busca por sequência | `GET similares?sequencia=<acordes>[&generos=<gênero>]` | `get_similares` via `sequencia` | `nome_musica`, `nome_artista`, `genero`, `popularidade`, `url` |

Todas as requisições do frontend são relativas (`apiUrl = ""`), então miram a mesma origem que serviu `index.html`. O frontend nunca envia `pagina`, então toda requisição usa a página padrão `'1'` do backend.

Os endpoints `/musicas`, `/generos`, `/acordes` e `/musica/<m_id>/` do backend não têm chamador no JavaScript carregado do frontend.

---

## 4. Arquivos de Dados e Pipeline Offline

### 4.1 Conjunto de dados de runtime — `data/top/dataset_final.csv`

- 15 MB, 67.586 linhas, sem cabeçalho.
- Nove colunas separadas por vírgula: `ARTISTA_ID`, `MUSICA_ID`, `ARTISTA`, `MUSICA`, `GENERO`, `POPULARIDADE`, `TOM`, `SEQ_FAMOSA`, `CIFRA`.
- Exemplo da primeira linha: `14-bis,a-qualquer-tempo,14 Bis,A Qualquer Tempo,MPB,70115,B,NA,E;F#;E;F#;C#m7;F#;B;E;...`
- `SEQ_FAMOSA` contém IDs de sequência separados por ponto e vírgula ou `NA`.
- `CIFRA` contém tokens de acordes separados por ponto e vírgula, incluindo acordes com barra, extensões e segmentos semelhantes a tablatura.
- Este é o único arquivo lido pela aplicação em execução (`main.py:49`).

### 4.2 Arquivos de dados auxiliares

| Arquivo | Tamanho / linhas | Conteúdo | Referenciado em runtime? |
|---|---|---|---|
| `data/top/visualizacoes.csv` | 69.960 linhas | `artista,musica,visualizacoes` com pontos como separador de milhares (ex.: `4.678`) | Não |
| `data/top/visualizacoes_pontos.csv` | 69.960 linhas | Mesmos dados com os pontos removidos (ex.: `4678`) | Não |
| `data/top/top_artistas.txt` | 999 linhas | URLs de artistas do CifraClub | Não |
| `data/top/top_artistas.txt_0.songs` | 25.017 linhas | Bloco 0 de URLs de músicas | Não |
| `data/top/top_artistas.txt_1.songs` | 25.004 linhas | Bloco 1 de URLs de músicas | Não |
| `data/top/top_artistas.txt_2.songs` | 19.426 linhas | Bloco 2 de URLs de músicas | Não |
| `data/top/top_artistas.txt_3.songs` | 471 linhas | Bloco 3 de URLs de músicas | Não |
| `data/top/artista_musica_estilo.txt` | 999 linhas | Triplas `artista,musica,estilo` | Não |
| `data/top/url-estilos.txt` | 75 linhas | URLs de estilos do CifraClub | Não |
| `data/top/html_estilos/` | 75 arquivos HTML | Páginas de estilo do CifraClub raspadas (ex.: `rock.html`) | Não |
| `data/top/chords-transitions-empty.csv` | 1 linha | Cabeçalho de 42 colunas de transições de acordes (`I-II` … `VII-VI`) | Não |
| `data/estilos.html` | 25.062 bytes | Página de índice de estilos do CifraClub | Não |
| `data/dataset_seq_notas.csv` | 66.526 linhas | Cabeçalho `"","ARTISTA","MUSICA","ESTILO","TOM","VISUALIZACOES","CIFRA","NCIFRA"`; sequências de acordes mais sequências normalizadas em algarismos romanos | Não |
| `data/transposition_matrix2.csv` | 13 linhas | Matriz de tonalidade/acorde para algarismo romano para as tonalidades de C a B | Não |
| `data/mapeamento_sequencias_famosas.txt` | 6 linhas | ID, nome, lista de acordes das seis sequências famosas | Não |
| `data/teoria` | 8 linhas | Notas de campo harmônico para F, C, G, D mais linhas de escala maior | Não |
| `data/data-cavaco.csv` | cabeçalho + linhas | `artista,musica,tom,sequencia` | Não |
| `data/cavaco_htlms.tar.gz` | arquivo | Páginas de cavaquinho raspadas | Não |
| `data/url-artistas.txt` | 63.671 linhas | Lista combinada de URLs de artistas | Não |
| `data/url-artistas-1.txt` | 20.000 linhas | Bloco de URLs de artistas | Não |
| `data/url-artistas-2.txt` | 20.000 linhas | Bloco de URLs de artistas | Não |
| `data/url-artistas-3.txt` | 20.000 linhas | Bloco de URLs de artistas | Não |
| `data/url-artistas-4.txt` | 3.671 linhas | Bloco de URLs de artistas | Não |
| `data/artistas_por_letra.txt` | 26 linhas | URLs do índice “artistas por letra” do CifraClub | Não |

`data/mapeamento_sequencias_famosas.txt` corresponde aos seis IDs em `main.py:40-45`:

```
0,Sequência de Bm,Bm - G - D - A
1,Sequência de C,C - G - Am - F
2,Sequência Em,Em - G
3,Sequência de C (Samba),C - A7 - Dm - G7
4,Sequência de Gm,Gm - F
5,Sequência de C (Samba cont.),C - C7 - F - Fm
```

### 4.3 Scripts offline

Esses scripts são autônomos; a aplicação Flask não os importa nem os executa.

#### Raspadores e transformadores Python

| Script | Linguagem / estado | O que faz | Referência |
|---|---|---|---|
| `scripts/generate_data_set.py` | Python 2 (`print` como instrução, `reload`, `setdefaultencoding`) | Raspa arquivos HTML do CifraClub com BeautifulSoup; extrai artista, música, título, gênero, tom, popularidade, sequência de acordes e tags de sequência famosa; imprime linhas CSV de nove colunas | `scripts/generate_data_set.py:1-92` |
| `scripts/cifra_parser.py` | Python 2 | Extrai artista, música, tom e notas de acordes do HTML raspado | `scripts/cifra_parser.py:1-27` |
| `scripts/parse_estilos.py` | Python 2 | Faz parsing de `estilos.html` e imprime URLs de estilos | `scripts/parse_estilos.py:1-22` |
| `scripts/parse_artistas_estilos.py` | Python 2 | Lista arquivos HTML; o corpo de parsing está comentado | `scripts/parse_artistas_estilos.py:1-29` |
| `scripts/add_estilos.py` | Python 2 | Junta `dataset_final.csv` com `artista_musica_estilo.txt` e escreve `test.csv` | `scripts/add_estilos.py:1-45` |

`generate_data_set.py` define as mesmas seis sequências famosas do runtime (`scripts/generate_data_set.py:7-24`) e emite a linha de nove colunas em `scripts/generate_data_set.py:89`.

#### Scripts R

| Script | Propósito | Referência |
|---|---|---|
| `data/top/merge_datasets.R` | Faz junção interna de `dataset.csv` e `visualizacoes_pontos.csv` por artista/música e escreve `dataset_final.csv` com cinco colunas (`ARTISTA`, `MUSICA`, `VISUALIZACOES`, `TOM`, `CIFRA`) | `data/top/merge_datasets.R:1-15` |
| `data/top/popularidade.R` | Lê `dataset_final.csv` e resume a popularidade por artista | `data/top/popularidade.R:1-10` |
| `scripts/add_estilos.R` | Faz junção à esquerda de `dataset_final.csv` com `artista_musica_estilo.txt` por artista | `scripts/add_estilos.R:1-10` |
| `scripts/normalize_chords.R` | Mapeia acordes para algarismos romanos usando `transposition_matrix2.csv`; produz `NCIFRA` | `scripts/normalize_chords.R:1-41` |
| `scripts/simplify_chords.R` | Mesmo mapeamento de `normalize_chords.R`, retornando o vetor de algarismos unido com `;` | `scripts/simplify_chords.R:1-36` |
| `scripts/build-chords-transitions.R` | Conta transições de acorde para acorde a partir de `data/dataset_seq_notas.csv` nas colunas de `chords-transitions-empty.csv` | `scripts/build-chords-transitions.R:1-77` |

O `data/top/dataset_final.csv` atual tem nove colunas, enquanto `merge_datasets.R` escreve cinco; o arquivo atual, portanto, inclui colunas adicionais além da saída desse script.

#### Raspadores shell e Java

| Script | Propósito | Referência |
|---|---|---|
| `scripts/collect_song_list.sh` | Executa `java -cp jsoup-1.8.3.jar:. DownloadAll <artists.txt>` | `scripts/collect_song_list.sh:1-6` |
| `scripts/download_band_names.sh` | Lê URLs do índice de artistas e faz `curl` de cada página para `<name>-artistas` | `scripts/download_band_names.sh:1-11` |
| `scripts/download_cifras.sh` | Lê URLs de músicas e faz `curl` de cada página para `cifras_erro/<artist>/` | `scripts/download_cifras.sh:1-9` |
| `scripts/DownloadAll.java` | Usa jsoup para coletar links de músicas de cada artista e escreve blocos de 25.000 URLs em arquivos `.songs` | `scripts/DownloadAll.java:14-73` |
| `scripts/jsoup-1.8.3.jar` | Dependência jsoup para `DownloadAll` | arquivo presente |
| `scripts/DownloadAll.class` | Classe `DownloadAll` compilada | arquivo presente |

---

## 5. Conexões entre Componentes e Fluxos de Dados

### 5.1 Fluxo de inicialização

```
data/top/dataset_final.csv
        │  (lido uma vez no import, main.py:49-98)
        ▼
musicas_dict / musicas (OrderedDict, popularidade desc)
genero_musicas (gênero → lista, popularidade desc)
generos (conjunto → lista)
acordes (conjunto)
sequencias (seis IDs)
        │
        ▼
Rotas Flask em main.py
```

Nenhuma requisição relê o CSV e nenhum processo escreve nele.

### 5.2 Fluxo da página de acordes

```
Navegador #/poracordes
  → AcordesController (static/assets/js/controllers/acordes.js)
  → GET /similares?acordes=C,G,Am,F[&generos=Rock]
  → main.get_similares (main.py:170-201)
  → apply_filtro (main.py:266-272)
  → get_similares (main.py:230-263)
      interseção/diferença contra os acordes de cada música
      ordena por (len(diferenca), -len(intersecao))
  → get_pagina (main.py:226-228) — primeiros 100
  → json.dumps
  → acordes.html renderiza cartões tocáveis vs. “aprender mais”
```

O template reordena a página por `-popularidade` no navegador (`acordes.html:42`, `66`).

### 5.3 Fluxo da página de música

```
Navegador #/pormusica
  → typeahead chama Musica.getMusicas(value)
  → GET /search?key=<texto>
  → main.busca (main.py:114-142)
      remove acentos, minúsculas, correspondência por token contra "artista título"
      apply_filtro + get_pagina
  → array JSON de correspondências leves
  → usuário seleciona uma música
  → GET /similares?id_unico_musica=<id>[&generos=<gênero>]
  → main.get_similares usa os acordes dessa música
  → mesmo caminho de similaridade/paginação da página de acordes
  → musica.html renderiza a música selecionada + cartões similares
```

### 5.4 Fluxo da página de sequência

```
Navegador #/porsequencia
  → SequenciaController tem quatro objetos de sequência locais
  → usuário clica em um ou muda o gênero
  → GET /similares?sequencia=Bm,G,D,A[&generos=Rock]
  → main.get_similares (main.py:190-197)
      remove vírgulas → "BmGDA"
      procura sequencias["BmGDA"] → 0
  → get_similares_por_sequencia(0, generos_key) (main.py:203-223)
      mantém músicas cujos seqs_famosas contêm "0"
  → get_pagina → primeiros 100
  → array JSON sem diferenca/intersecao
  → sequencia.html renderiza cartões ordenados por -popularidade
```

Strings de sequência desconhecidas retornam `[]` sem cair no caminho de similaridade por acordes (`main.py:194-197`).

### 5.5 Fluxo do filtro de gênero

```
Valor do dropdown do frontend (uma string de GENEROS)
  → parâmetro de consulta generos=<valor>
  → request.args.get('generos')
  → split(',') se presente, senão todos os generos
  → apply_filtro itera os nomes solicitados
  → apenas nomes presentes no conjunto global generos contribuem com músicas
  → listas por gênero concatenadas, cada uma já em ordem decrescente de popularidade
```

A lista do frontend contém 51 nomes; o conjunto do backend contém 52. O valor `R&B;` do backend não é selecionável no dropdown do frontend.

### 5.6 Fluxo de paginação

- Apenas `/search` e `/similares` chamam `get_pagina` (`main.py:142`, `196`, `201`).
- O tamanho da página é 100 (`main.py:35`).
- O frontend nunca envia `pagina`, então sempre recebe a página 1.
- `/musicas` retorna todos os 67.585 registros e ignora a paginação.
- `/musica/<m_id>/` retorna um único registro e não pagina.

### 5.7 Matriz de formato de resposta

| Endpoint / modo | Paginado | Inclui `popularidade` | Inclui `acordes` | Inclui `diferenca` / `intersecao` | Inclui `url` |
|---|---|---|---|---|---|
| `/search` | Sim | Não | Não | Não | Sim |
| `/similares?acordes=` | Sim | Sim | Sim | Sim | Sim |
| `/similares?id_unico_musica=` | Sim | Sim | Sim | Sim | Sim |
| `/similares?sequencia=` | Sim | Sim | Sim | Não | Sim |
| `/musicas` | Não | Sim | Sim | Não | Sim |
| `/musica/<m_id>/` | Não | Sim | Sim | Não | Sim |

`/musicas` e `/musica/<m_id>/` retornam o `Musica.__dict__` completo, que também inclui `id_artista`, `nome_artista`, `id_musica`, `nome_musica`, `genero`, `tom`, `cifra`, `seqs_famosas` e `id_unico_musica` (`musica.py:7-22`).

---

## 6. Documentação e Arquivos de Configuração

| Arquivo | Conteúdo atual | Referência |
|---|---|---|
| `README.md` | Descrição do projeto, instruções de execução com Docker e virtualenv, links para `CONTRIB.md` e `LICENSE` | `README.md:1-35` |
| `AGENTS.md` | Resumo da stack (Flask/Python 3.9, AngularJS 1.4.9 + jQuery, sem etapa de build, CSV em memória, Docker local-only), comandos de execução, comando de verificação de `/generos`, observações sobre recarga do CSV e respostas `json.dumps` | `AGENTS.md:1-47` |
| `CONTRIB.md` | Modelo de CLA e contribuição do app de exemplo do Google Cloud Platform | `CONTRIB.md:1-38` |
| `LICENSE` | Licença Apache 2.0 | `LICENSE:1-201` |
| `docs/adr/0001-local-only-docker-deploy.md` | Decisão de remover a configuração do App Engine/Heroku e usar um único Dockerfile local-only; afirma que a arquitetura do backend foi mantida inalterada | `docs/adr/0001-local-only-docker-deploy.md:1-16` |
| `docs/adr/0002-persist-custom-sequences.md` | Modelo não preenchido com texto provisório para uma decisão de persistência | `docs/adr/0002-persist-custom-sequences.md:1-8` |
| `docs/adr/0003-lift-frontend-freeze.md` | Decisão de remover a restrição de mexer no frontend AngularJS; a stack em si continua AngularJS 1.4.9 + jQuery sem etapa de build | `docs/adr/0003-lift-frontend-freeze.md:1-21` |
| `docs/features/sequencias-customizadas/00-enunciado.md` | Enunciado do trabalho de full-stack para sequências de acordes customizadas; descreve as seis sequências atuais do backend e as quatro do frontend | `docs/features/sequencias-customizadas/00-enunciado.md:1-130` |
| `docs/features/sequencias-customizadas/01-research.md` | Modelo da fase de pesquisa com perguntas e seções de descobertas vazias | `docs/features/sequencias-customizadas/01-research.md:1-44` |
| `docs/features/sequencias-customizadas/02-proposal.md` | Modelo da fase de proposta com seções vazias | `docs/features/sequencias-customizadas/02-proposal.md:1-49` |
| `docs/features/sequencias-customizadas/03-plan.md` | Modelo da fase de plano com passos e tabela de arquivos vazios | `docs/features/sequencias-customizadas/03-plan.md:1-33` |
| `docs/features/sequencias-customizadas/04-test-report.md` | Modelo de relatório de testes com seções de cobertura e regressão vazias | `docs/features/sequencias-customizadas/04-test-report.md:1-25` |
| `.playground` | Metadados do starter do Google App Engine listando `main.py`, `app.yaml` e `appengine_config.py`; `app.yaml` e `appengine_config.py` não estão presentes na árvore atual | `.playground:1-13` |

`docs/features/sequencias-customizadas/01-research.md:9-13` e `00-enunciado.md:26-31` descrevem os mesmos fatos de runtime encontrados no código: seis sequências no backend em `main.py`, quatro sequências no frontend em JavaScript e uma tag `SEQ_FAMOSA` pré-computada no CSV.

---

## 7. Resultados Observados dos Endpoints ao Vivo

A aplicação foi iniciada localmente com gunicorn (`Flask 3.1.3`, `gunicorn 23.0.0`) contra a árvore de trabalho atual. Resultados:

| Requisição | Status | Resultado observado |
|---|---|---|
| `GET /generos` | 200, `text/html; charset=utf-8` | Array JSON de 52 nomes de gêneros |
| `GET /acordes` | 200 | Array JSON de 6.653 strings de acordes |
| `GET /musicas` | 200 | Array JSON de 67.585 objetos completos de música |
| `GET /search?key=californication` | 200 | 3 correspondências, primeira `red-hot-chili-peppers_californication` |
| `GET /similares?id_unico_musica=14-bis_adoraveis-criaturas` | 200 | 100 resultados; o primeiro tinha `diferenca` de tamanho 0 e `intersecao` de tamanho 9 |
| `GET /similares?acordes=C,G,Am,F&generos=Rock` | 200 | 100 resultados; o primeiro era `Fallen Angels` (gênero `Rock`) |
| `GET /similares?sequencia=BmGDA` | 200 | 100 resultados (página 1) |
| `GET /similares?sequencia=CGAmF` | 200 | 100 resultados na página 1, 100 na página 2, 96 na página 3 |
| `GET /similares?sequencia=EmG` | 200 | 4 resultados |
| `GET /similares?sequencia=CA7DmG7` | 200 | 5 resultados |
| `GET /similares?sequencia=GmF` | 200 | 7 resultados |
| `GET /similares?sequencia=CC7FFm` | 200 | 3 resultados |
| `GET /similares?sequencia=ZZZ` | 200 | `[]` |
| `GET /musica/14-bis_adoraveis-criaturas/` | 200 | Um objeto de música; `seqs_famosas` era `['']` |
| `GET /` | 200, `text/html; charset=utf-8` | `static/index.html` |
| `GET /assets/js/app.js` | 200, `text/javascript; charset=utf-8` | Arquivo estático |
| `GET /nope` | 404 | O proxy estático não encontrou arquivo |
| `GET /search` (sem `key`) | 500 | `AttributeError: 'NoneType' object has no attribute 'lower'` em `main.py:118` |
| `GET /musica/nope/` | 500 | `KeyError: 'nope'` em `main.py:168` |

Toda resposta carregava `Access-Control-Allow-Origin: *` de `main.py:274-277`. As respostas de API carregavam `Content-Type: text/html; charset=utf-8` porque os handlers retornam strings `json.dumps(...)`.

---

## 8. Resumo do Inventário de Arquivos

| Área | Arquivos |
|---|---|
| Backend | `main.py`, `musica.py`, `requirements.txt`, `Dockerfile` |
| Shell do frontend | `static/index.html`, `static/favicon.ico`, `static/bower.json` |
| JavaScript do frontend | `static/assets/js/app.js`, `routes.js`, `ngprogress.js`, `controllers/*.js` (7 arquivos), `directives/df-hex.js`, `directives/df-esfinge.js` |
| Templates do frontend | `static/templates/home.html`, `acordes.html`, `musica.html`, `sequencia.html`, `about.html`, `templates/directives/df-hex.html`, `templates/directives/df-esfinge.html` |
| Assets do frontend | `static/assets/css/app.css`, `icons.css`, `fonts/icomoon.*`, `img/deciframe.png`, `img/team.png` |
| Dados de runtime | `data/top/dataset_final.csv` |
| Dados auxiliares | `data/top/*`, `data/*.csv`, `data/*.txt`, `data/teoria`, `data/estilos.html`, snapshots de `data/top/html_estilos`, `data/cavaco_htlms.tar.gz` |
| Scripts offline | `scripts/*.py`, `scripts/*.R`, `scripts/*.sh`, `scripts/DownloadAll.java`, `scripts/DownloadAll.class`, `scripts/jsoup-1.8.3.jar`, `data/top/*.R` |
| Documentação | `README.md`, `AGENTS.md`, `CONTRIB.md`, `LICENSE`, `docs/adr/*`, `docs/features/sequencias-customizadas/*` |
| Metadados do repositório | `.gitignore`, `.dockerignore`, `.playground` |
