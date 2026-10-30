# Pesquisa — Busca por Sequências de Acordes no Estado Atual

**Data:** 2026-10-30  
**HEAD:** `c0a7777` — `docs: adiciona pesquisa do código atual em português`  
**Escopo:** funcionamento atual da busca por “sequência famosa” (`GET /similares?sequencia=...`) no backend, no frontend e nos dados.

## Resumo

A busca por sequência é um caminho separado dentro de `GET /similares`: o backend remove as vírgulas do parâmetro recebido, procura a string resultante em um dicionário literal de seis chaves (`main.py:40-45`) e, se encontrar, filtra o catálogo pela tag pré-computada `seqs_famosas` de cada música (`main.py:190-197`, `main.py:203-223`). A tag vem da coluna `SEQ_FAMOSA` do CSV, dividida por `;` durante a carga (`main.py:63`) e armazenada no objeto `Musica` (`musica.py:18`). O frontend `#/porsequencia` mantém quatro sequências próprias em JavaScript (`sequencia.js:2-37`), monta a requisição concatenando os acordes com vírgulas (`sequencia.js:55-61`, `sequencia.js:73`) e renderiza a resposta sem campo `diferenca` (`sequencia.html:41-43`). Não há, no código de runtime, cálculo de ocorrência de uma sequência de acordes sobre a cifra de uma música: a única verificação existente é a pertinência de um ID na lista `seqs_famosas` (`main.py:209`). Também não há rota de escrita, armazenamento ou banco de dados para sequências cadastradas.

---

## 1. Superfície HTTP da busca por sequência

### 1.1 Rota e precedência de parâmetros

`GET /similares` é tratado por `get_similares()` (`main.py:170-201`). Os parâmetros lidos são `acordes`, `id_unico_musica`, `sequencia`, `pagina` e `generos` (`main.py:173-176`).

A seleção da origem dos acordes usa uma cadeia `if`/`elif` (`main.py:184-197`):

| Ordem | Condição | Efeito |
|---|---|---|
| 1 | `acordes` presente | Usa `acordes_tag.split(',')`; ignora `sequencia` e `id_unico_musica` |
| 2 | senão, `id_unico_musica` presente | Usa `musicas[id_musica_tag].acordes`; ignora `sequencia` |
| 3 | senão, `sequencia` presente | Remove as vírgulas e procura a string no dicionário `sequencias` |
| 4 | nenhum dos três | Chama `get_similares([], ...)` |

No caso 3, a variável `acordes` recebe `sequencia_tag.replace(',', '')` (`main.py:191`). Se a string existir em `sequencias`, o handler chama `get_similares_por_sequencia(id_seq, generos_key)` e pagina o resultado (`main.py:194-196`). Se não existir, retorna `json.dumps([])` (`main.py:197`). O `return` do caso 3 encerra o handler, então uma sequência desconhecida não segue para o caminho de similaridade por acordes.

### 1.2 Dicionário de sequências

As seis chaves são declaradas em `main.py:40-45`:

| Chave procurada | ID | Acordes correspondentes |
|---|---|---|
| `BmGDA` | `0` | `Bm`, `G`, `D`, `A` |
| `CGAmF` | `1` | `C`, `G`, `Am`, `F` |
| `EmG` | `2` | `Em`, `G` |
| `CA7DmG7` | `3` | `C`, `A7`, `Dm`, `G7` |
| `GmF` | `4` | `Gm`, `F` |
| `CC7FFm` | `5` | `C`, `C7`, `F`, `Fm` |

A chave é a concatenação dos nomes dos acordes, sem separador. Por isso o frontend envia `sequencia=Bm,G,D,A` e o backend a converte em `BmGDA`. A comparação é exata: diferencia maiúsculas de minúsculas, considera espaços e depende da ordem dos acordes.

### 1.3 Filtro de gênero e paginação

O filtro de gênero segue o mesmo padrão de `/search`: sem `generos`, usa a lista global `generos`; com `generos`, divide o valor por vírgulas (`main.py:179-182`). `apply_filtro` ignora a coleção recebida, itera os nomes solicitados e concatena `genero_musicas[genero]` para os nomes presentes no conjunto global (`main.py:266-272`).

A paginação usa `get_pagina`, que fatia de `(int(pagina_tag) - 1) * 100` até mais 100 (`main.py:226-228`), com `TAM_PAGINA = 100` (`main.py:35`). O frontend não envia `pagina`, então a busca por sequência usa o padrão `'1'` (`main.py:176`).

### 1.4 Formato da resposta

Cada item retornado no modo sequência contém (`main.py:210-220`):

- `id_unico_musica`
- `id_artista`
- `id_musica`
- `nome_artista`
- `nome_musica`
- `popularidade`
- `acordes`
- `genero`
- `url`

O campo `acordes` é a lista deduplicada de acordes da música (`musica.py:17`), não a sequência consultada. A resposta não inclui `diferenca`, `intersecao`, `seqs_famosas`, `tom` nem `cifra`. Como todos os handlers usam `json.dumps(...)` diretamente (`main.py:197`), a resposta sai com `Content-Type: text/html; charset=utf-8`.

---

## 2. Backend: como o match é feito hoje

### 2.1 `get_similares_por_sequencia`

`get_similares_por_sequencia(id_seq, generos_key)` (`main.py:203-223`) executa dois passos:

1. Filtra o catálogo por gênero com `apply_filtro(musicas.values(), generos_key)` (`main.py:205`).
2. Percorre a coleção e mantém a música quando `str(id_seq) in musica.seqs_famosas` (`main.py:209`).

Não há comparação entre a sequência consultada e `musica.cifra` ou `musica.acordes` nessa função. O ID já foi resolvido pelo dicionário `sequencias` antes da chamada. A ordenação do resultado é a ordem da coleção filtrada: gêneros na ordem de `generos_key` e, dentro de cada gênero, popularidade decrescente estabelecida na carga (`main.py:95-96`). A função não reordena.

### 2.2 Caminho de similaridade por acordes

O outro caminho de `/similares` chama `get_similares(acordes, generos_key, id_musica)` (`main.py:230-263`). Ele calcula:

- `inter = set(acordes).intersection(set(musica.acordes))` (`main.py:240`)
- `diff = set(musica.acordes) - set(acordes)` (`main.py:241`)

Mantém músicas com interseção não vazia (`main.py:245`) e ordena por `(len(diferenca), -len(intersecao))` (`main.py:263`). Essa lógica opera sobre conjuntos de acordes; não verifica ordem, repetição ou contiguidade de uma sequência na cifra.

### 2.3 Ausência de cálculo em tempo real e de escrita

- A única verificação de correspondência que usa `seqs_famosas` é a pertinência em `main.py:209`; as demais referências apenas dividem, armazenam ou expõem a lista (`main.py:63`, `main.py:71`, `musica.py:18`, `main.py:156`, `main.py:168`).
- Todas as rotas declaradas em `main.py` são `GET` (`main.py:101`, `109`, `114`, `154`, `158`, `162`, `166`, `170`). Não há rota `POST`, `PUT` ou `DELETE`.
- Não há banco de dados, ORM, migração ou camada de persistência no runtime; `requirements.txt` lista apenas `Flask` e `gunicorn` (`requirements.txt:4-5`), e o estado é reconstruído do CSV a cada início (`main.py:49-98`).
- O dicionário `sequencias` é um literal de módulo (`main.py:40-45`), sem carga de configuração, arquivo ou banco.

---

## 3. Dados: a coluna `SEQ_FAMOSA`

### 3.1 Carga e armazenamento

O CSV `data/top/dataset_final.csv` não tem cabeçalho; a primeira linha é descartada com `f.readline()` (`main.py:49-50`). Cada linha restante é dividida por vírgulas (`main.py:55`), e o campo de índice `SEQ_FAMOSA = 7` (`main.py:33`) é dividido por `;` (`main.py:63`) antes de ser passado ao construtor de `Musica` (`main.py:71`). O objeto armazena a lista em `self.seqs_famosas` (`musica.py:18`).

O campo aparece em respostas que expõem `Musica.__dict__`: `/musicas` (`main.py:156`) e `/musica/<m_id>/` (`main.py:168`). A resposta do modo sequência não o inclui (`main.py:210-220`). Como `NA` é removido em `main.py:53`, registros sem sequência ficam com `seqs_famosas == ['']` após o split de `main.py:63`.

### 3.2 Distribuição atual

Medição sobre o CSV atual (67.586 linhas físicas; 67.585 registros carregados):

| Valor na coluna `SEQ_FAMOSA` | Registros |
|---|---|
| `NA` | 67.071 |
| `1` | 296 |
| `0` | 199 |
| `4` | 7 |
| `3` | 5 |
| `2` | 4 |
| `5` | 3 |

Não há valores com `;` no CSV atual, ou seja, cada registro carregado tem no máximo um ID de sequência. Exemplos de linhas com tag: `30-seconds-to-mars,city-of-angels,30 Seconds To Mars,City Of Angels,Alternativo,16307,D,0` e `5-seconds-of-summer,bad-dreams,5 Seconds Of Summer,Bad Dreams,Pop Rock,1105,C,1`.

### 3.3 Geração offline da tag

A tag é produzida pelo script Python 2 `scripts/generate_data_set.py`, que não é importado pela aplicação. A função `get_famosas` (`scripts/generate_data_set.py:7-24`) define seis sequências em minúsculas (`scripts/generate_data_set.py:8`) e, para cada uma:

1. Verifica se a string da sequência é substring da string de acordes da música em minúsculas (`scripts/generate_data_set.py:12-13`).
2. Verifica se cada token da string de acordes da música pertence ao conjunto de tokens da sequência (`scripts/generate_data_set.py:16-20`).
3. Se as duas condições valem, acrescenta o índice da sequência ao resultado (`scripts/generate_data_set.py:21-23`).

O script monta a string de acordes a partir das tags `<b>` da página raspada (`scripts/generate_data_set.py:69-76`), chama `get_famosas` e grava o resultado na oitava coluna; sem match, grava `NA` (`scripts/generate_data_set.py:84-89`). O resultado é concatenado com `''.join(...)`, sem separador entre IDs (`scripts/generate_data_set.py:88`); no CSV atual não há registro com mais de um ID.

O arquivo `data/mapeamento_sequencias_famosas.txt:1-6` lista os mesmos seis IDs, nomes e acordes, mas não é lido pelo runtime.

---

## 4. Frontend: rota `#/porsequencia`

### 4.1 Rota, script e controller

A rota `/porsequencia` usa `templates/sequencia.html` e `SequenciaController` com o apelido `Sequencia` (`static/assets/js/routes.js:17-21`). O controller é carregado em `static/index.html:145`. A home linka para a rota em `static/templates/home.html:79-82`.

`SequenciaController` (`static/assets/js/controllers/sequencia.js:1-105`) declara quatro objetos locais:

| Objeto | Acordes | ID correspondente no backend |
|---|---|---|
| `sequencia1` | `Bm`, `G`, `D`, `A` | `0` |
| `sequencia2` | `C`, `G`, `Am`, `F` | `1` |
| `sequencia3` | `Gm`, `F` | `4` |
| `sequencia4` | `C`, `C7`, `F`, `Fm` | `5` |

As declarações estão em `sequencia.js:2-31`; os quatro objetos são inseridos em `vm.sequenciasFamosas` em `sequencia.js:33-37`. Cada acorde é um objeto `{acorde, cor}` com a mesma cor `#2E1C74`. Os IDs `2` (`EmG`) e `3` (`CA7DmG7`) existem no backend, mas não têm objeto nem botão no frontend. Não há rota que liste as sequências; a lista exibida vem apenas do controller.

### 4.2 Montagem da requisição

`createChordsString` percorre a lista e concatena `chords[i].acorde` com `,`, removendo a última vírgula (`sequencia.js:55-61`). `pesquisarPorSequencia` (`sequencia.js:63-90`):

- Usa a sequência recebida ou `vm.minhaSequencia` (`sequencia.js:64-66`).
- Define `apiUrl = ""` (`sequencia.js:72`).
- Monta `similares?sequencia=` + a string de acordes (`sequencia.js:73`).
- Anexa `&generos=<valor>` quando `vm.meuGenero` não é vazio nem `null` (`sequencia.js:74-76`).
- Chama `$http.get(apiUrl.concat(searchString))` (`sequencia.js:77`).
- Atribui a resposta diretamente a `vm.musics` (`sequencia.js:83`).

A requisição não envia `pagina`. Os acordes são enviados na ordem do array e sem espaços, por exemplo `sequencia=Bm,G,D,A`.

### 4.3 Template

`static/templates/sequencia.html:1-63`:

- Renderiza as quatro sequências com `ng-repeat` sobre `Sequencia.sequenciasFamosas`; o clique no contêiner chama `Sequencia.pesquisarPorSequencia(sequencia)` (`sequencia.html:6`).
- Cada acorde é renderizado pela diretiva `df-hex`, com `acorde-checked="Sequencia.temAcorde(acordeon)"` (`sequencia.html:7`).
- O dropdown de gênero usa `Sequencia.generos` (a constante `GENEROS`) e chama `Sequencia.pesquisarPorSequencia()` na mudança (`sequencia.html:24-30`).
- Os acordes da sequência selecionada são renderizados a partir de `Sequencia.minhaSequencia.acordes`; o clique chama `Sequencia.limparPesquisa()` (`sequencia.html:34`), que zera `vm.minhaSequencia` e `vm.musics` (`sequencia.js:92-95`).
- Os resultados usam `ng-repeat="music in Sequencia.musics | orderBy:'-popularidade'"` e `ng-hide="music.diferenca.length"` (`sequencia.html:41-43`). O campo `diferenca` não existe na resposta do modo sequência (`main.py:210-220`).
- Cada cartão exibe `nome_musica`, `nome_artista` e `genero` e abre `music.url` em nova janela (`sequencia.html:45-56`, `sequencia.js:97-99`).

A constante `GENEROS` tem 51 entradas (`static/assets/js/app.js:6-58`); o conjunto de gêneros do backend tem 52, incluindo `R&B;`.

---

## 5. Fluxo ponta a ponta e contrato

### 5.1 Fluxo da busca por sequência

```
Navegador #/porsequencia
  → SequenciaController (static/assets/js/controllers/sequencia.js:63-90)
  → GET similares?sequencia=Bm,G,D,A[&generos=Rock]
  → main.get_similares (main.py:170-201)
      remove vírgulas → "BmGDA"
      sequencias["BmGDA"] → 0
  → get_similares_por_sequencia(0, generos_key) (main.py:203-223)
      apply_filtro por gênero (main.py:205, 266-272)
      mantém músicas com "0" em musica.seqs_famosas (main.py:209)
  → get_pagina (main.py:226-228) → primeiros 100
  → json.dumps (main.py:197)
  → sequencia.html renderiza cartões (sequencia.html:41-58)
```

### 5.2 Regras de correspondência da string

| Entrada `sequencia` | String procurada | Resultado |
|---|---|---|
| `Bm,G,D,A` | `BmGDA` | Encontra ID `0` |
| `BmGDA` | `BmGDA` | Encontra ID `0` |
| `bm,g,d,a` | `bmgda` | Não encontra; retorna `[]` |
| `Bm, G, D, A` | `Bm G D A` | Não encontra; retorna `[]` |
| `Bm,G,D,A,Em` | `BmGDAEm` | Não encontra; retorna `[]` |
| `Am,F,C,G` | `AmFCG` | Não encontra; retorna `[]` |

### 5.3 Formatos de resposta relacionados

| Requisição | Campos específicos |
|---|---|
| `/similares?sequencia=` | `id_unico_musica`, `id_artista`, `id_musica`, `nome_artista`, `nome_musica`, `popularidade`, `acordes`, `genero`, `url` |
| `/similares?acordes=` | Os mesmos acima mais `diferenca` e `intersecao` |
| `/musicas`, `/musica/<m_id>/` | `Musica.__dict__` completo, incluindo `seqs_famosas`, `tom` e `cifra` |

---

## 6. Verificação ao vivo

Execução local com `Flask 3.1.3` via test client, contra a árvore atual:

| Requisição | Status | Resultado |
|---|---|---|
| `/similares?sequencia=Bm,G,D,A` | 200 | 100 itens na página 1; 99 na página 2 |
| `/similares?sequencia=BmGDA` | 200 | 100 itens na página 1 |
| `/similares?sequencia=CGAmF` | 200 | 100 / 100 / 96 nas páginas 1–3 |
| `/similares?sequencia=EmG` | 200 | 4 itens |
| `/similares?sequencia=CA7DmG7` | 200 | 5 itens |
| `/similares?sequencia=GmF` | 200 | 7 itens |
| `/similares?sequencia=CC7FFm` | 200 | 3 itens |
| `/similares?sequencia=Bm,G,D,A&generos=Rock` | 200 | 5 itens; primeiro `Bang a drum` / `Bon Jovi` |
| `/similares?sequencia=bm,g,d,a` | 200 | `[]` |
| `/similares?sequencia=Bm, G, D, A` | 200 | `[]` |
| `/similares?sequencia=Bm,G,D,A,Em` | 200 | `[]` |
| `/similares?sequencia=C,G,Am` | 200 | `[]` |
| `/similares?sequencia=Am,F,C,G` | 200 | `[]` |
| `/similares?sequencia=ZZZ` | 200 | `[]` |

Todas as respostas tiveram `Content-Type: text/html; charset=utf-8` e `Access-Control-Allow-Origin: *` (`main.py:274-277`).

---

## 7. Arquivos envolvidos

| Arquivo | Papel no estado atual |
|---|---|
| `main.py` | Dicionário `sequencias`, parsing de `SEQ_FAMOSA`, rota `/similares`, `get_similares_por_sequencia`, paginação e filtro de gênero |
| `musica.py` | Armazena `seqs_famosas`, `cifra` e `acordes` por música |
| `data/top/dataset_final.csv` | Fonte da coluna `SEQ_FAMOSA` e das cifras |
| `data/mapeamento_sequencias_famosas.txt` | Lista nominal das seis sequências; não lida em runtime |
| `scripts/generate_data_set.py` | Geração offline da tag `SEQ_FAMOSA` |
| `static/assets/js/controllers/sequencia.js` | Quatro sequências hardcoded, montagem da requisição e estado da tela |
| `static/templates/sequencia.html` | Renderização dos botões, filtro de gênero e cartões de resultado |
| `static/assets/js/routes.js` | Rota `/porsequencia` |
| `static/assets/js/app.js` | Constante `GENEROS` usada no filtro |
| `static/index.html` | Carrega o controller `sequencia.js` |
| `static/templates/home.html` | Link para `#/porsequencia` |
