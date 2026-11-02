# Propostas de Solução — Sequências de Acordes Customizadas

> Documento de apoio à fase 02. Ele apresenta duas alternativas e não substitui
> `02-proposal.md`, que deve registrar a abordagem final escolhida.

## Solution Proposals

Context:
- **Request:** permitir que qualquer visitante cadastre uma sequência de acordes e busque músicas por ela, com catálogo persistido em banco, mantendo resultados idênticos para as 6 sequências atuais e o CSV como fonte de músicas/gêneros.
- **Research Source:** `docs/features/sequencias-customizadas/01-research.md` (perguntas 1–4 e trade-offs, especialmente `:38-42`), `docs/features/sequencias-customizadas/generated/sequencias-famosas-estado-atual.md` (seções 1–5, contrato atual e `:200-209`), `docs/features/sequencias-customizadas/generated/codebase-overview.md` (stack, rotas e frontend) e `generated/validate_matching.py` (validação empírica dos algoritmos).
- **Evidência empírica:** executando `validate_matching.py`, o algoritmo histórico `set(cifra) <= set(seq) and contiguous(cifra, seq)` reproduz exatamente a tag `SEQ_FAMOSA` nas 6 sequências: `199, 296, 4, 5, 7, 3` músicas. Já o matching contíguo simples encontra `866, 1216, 3110, 96, 1039, 132` — ou seja, muda radicalmente as 6. Para sequências novas, o critério histórico é quase inútil: `C-G` encontra 20 músicas, contra 11.877 no contíguo; `C-G-Am` encontra 28, contra 2.571.
- **Research Gaps:** a pesquisa compara algoritmos, mas não decide a semântica desejada para sequências novas; também não fixa política de duplicatas, limites, normalização de acordes/transposição, moderação do catálogo anônimo nem detalhes de volume Docker/SQLite sob gunicorn. Esses pontos precisam de decisão antes da implementação.

---

### Proposal 1 — Catálogo SQLite com matching híbrido por modo (recomendada)

- **Overview:** o catálogo passa a viver em SQLite. As 6 sequências originais são seedadas com `match_mode = 'legacy_tag'` e continuam usando a tag `seqs_famosas` do CSV; sequências novas entram com `match_mode = 'contiguous'` e são calculadas em tempo real sobre `musica.cifra`. Isso preserva a regressão por construção e dá semântica intuitiva para o catálogo novo.

- **Key Changes:**
  - **Persistência:** novo módulo `db.py` usando `sqlite3` da stdlib, sem nova dependência em `requirements.txt`. Banco em `app.instance_path/deciframe.db` (ou `DECIFRAME_DB`), com `PRAGMA journal_mode=WAL` e `busy_timeout`.
  - **Schema:** `sequencias(id, nome, acordes_json, chave UNIQUE, match_mode, legacy_id, criado_em)`. `chave` é a lista de acordes normalizada e ordenada por posição; `legacy_id` guarda `0..5` para as originais. Seed idempotente a partir de `data/mapeamento_sequencias_famosas.txt:1-6` ou de constantes equivalentes.
  - **Backend (`main.py`):** remover o dicionário `sequencias` de `main.py:40-45` como fonte de verdade; manter apenas resolução de compatibilidade. Em `/similares` (`main.py:170-201`), aceitar `sequencia_id` e continuar aceitando `sequencia=...`. Para `legacy_tag`, reutilizar `get_similares_por_sequencia` (`main.py:203-223`); para `contiguous`, varrer `musica.cifra` com sublista contígua. Reutilizar `apply_filtro` (`main.py:266-272`), `get_pagina` (`main.py:226-228`) e o mesmo formato de resposta de `main.py:210-220`.
  - **API:** `GET /sequencias` retorna o catálogo; `POST /sequencias` recebe `{"nome": "...", "acordes": ["C","G","Am"]}` e cria com `contiguous` por padrão. Duplicata exata de `chave` retorna `409` com o `id` existente. Erros continuam com `json.dumps(...)`, não `jsonify`.
  - **Frontend:** em `static/assets/js/controllers/sequencia.js:2-37`, remover as 4 sequências hardcoded; carregar `GET sequencias` na inicialização. Adicionar formulário em `static/templates/sequencia.html:6-8` com nome e lista de acordes, `POST` e recarga do catálogo. Buscar preferencialmente por `sequencia_id`; manter o formato `sequencia=C,G,Am` para compatibilidade. Corrigir o `ng-hide="music.diferenca.length"` inócuo em `sequencia.html:41-43`.
  - **Deploy:** manter o `Dockerfile:1-12` de container único. Documentar `docker run -v ciframe-instance:/app/instance -p 8080:8080 ciframe`; **não** montar volume em `/app/data`, pois isso esconderia `data/top/dataset_final.csv`. Adicionar `instance/` a `.gitignore` e `.dockerignore`.
  - **Testes:** novo `tests/` com `unittest` + `Flask.test_client`, banco temporário via `DECIFRAME_DB`; fixture dourada com os IDs das 6 sequências antes da mudança.

- **Trade-offs:**
  - **Prós:** regressão exata sem reescrever a tag histórica; sequências novas com resultados úteis; catálogo realmente persistido e backend-driven; nenhum serviço externo; SQLite é stdlib e cabe no container.
  - **Contras:** duas semânticas de matching no mesmo catálogo; as 6 originais ficam dependentes da tag `SEQ_FAMOSA` (se o CSV mudar, os resultados mudam); uma sequência nova idêntica a uma original não pode usar a semântica contígua sem conflito de duplicata; mais caminhos para testar; catálogo anônimo exige limites de tamanho e, idealmente, moderação/rate limit fora do escopo.
  - **Performance:** o modo legado é uma checagem de pertinência; o contíguo varre ~59 mil músicas com cifra. Para uso local tende a ser aceitável, mas convém medir e, se necessário, cachear resultados por `sequencia_id` ou construir um índice de n-gramas em memória no startup.

- **Validation:**
  - **Regressão obrigatória:** capturar antes/depois os IDs por página para as 6, nas formas `sequencia=BmGDA` e `sequencia=Bm,G,D,A`, com e sem `generos`. Comparar lista exata, não só contagem. O `validate_matching.py` já prova que o critério legado calculado é igual à tag; aqui o teste prova que o seed roteia corretamente para o modo legado.
  - **Novas sequências:** `C-G` deve retornar 11.877 candidatos (paginados de 100 em 100); verificar uma música conhecida como `14-bis_eu-ja-fechei-meus-olhos`. Testar ordem, repetição e não contiguidade: `G-C` não deve casar onde só existe `C-G`.
  - **API:** `GET /sequencias` com 6 seeds; `POST` válido → `201`; duplicata → `409`; nome vazio, lista vazia, acorde vazio e JSON inválido → `400`; busca por `sequencia_id`; busca por string legada; `sequencia_id` inexistente → `[]` ou `404`, conforme contrato escolhido; paginação e filtro de gênero; `Content-Type: text/html` preservado.
  - **Persistência:** criar sequência, reiniciar gunicorn, `docker restart`, e `docker rm` + `docker run` com o mesmo volume; o catálogo deve permanecer. Confirmar que o CSV continua carregando normalmente.
  - **Frontend:** checklist manual/E2E: página lista as 6; cadastro de `C,G,Am` aparece na lista; clique busca; filtro de gênero funciona; reload mantém; erros de validação aparecem. Não há harness de frontend no projeto; decidir se vale adicionar um smoke test de browser.

- **Open Questions:**
  - O `match_mode` deve ser visível na UI (“clássica” vs “tempo real”) ou transparente?
  - As 6 seeds podem ser editadas/excluídas? Recomendo read-only.
  - Duplicata: comparar só a lista normalizada de acordes, ou também o nome? O que fazer se o usuário cadastrar a mesma sequência de uma original querendo semântica contígua?
  - Aceitar acordes fora do conjunto `/acordes` (6.653 tokens) ou rejeitar/avisar?
  - Limites de nome, quantidade de acordes e tamanho do payload; moderação do catálogo anônimo.
  - Normalização futura: espaços, maiúsculas/minúsculas, enarmonia (`C#` vs `Db`) e transposição ficam fora do escopo?
  - Migrar as 6 originais para matching calculado no futuro ou manter a tag histórica indefinidamente?

---

### Proposal 2 — Catálogo SQLite com matching estrito uniforme (legado calculado)

- **Overview:** todas as sequências, incluindo as 6 originais, usam a mesma regra calculada em tempo real: a sequência é uma sublista contígua da cifra **e** todos os acordes da música pertencem ao conjunto da sequência (`set(cifra) <= set(seq) and contiguous(cifra, seq)`). É exatamente o critério de `scripts/generate_data_set.py:7-24` e de `validate_matching.py:78-83`, o que garante regressão exata sem depender da tag `SEQ_FAMOSA` para busca.

- **Key Changes:**
  - **Persistência:** `db.py` com schema mais simples: `sequencias(id, nome, acordes_json, chave UNIQUE, criado_em)`. Sem `match_mode` e sem `legacy_id`; seed das 6 com o mesmo schema das novas.
  - **Backend (`main.py`):** substituir `get_similares_por_sequencia` (`main.py:203-223`) por uma função que recebe a lista de acordes da sequência e aplica o critério estrito sobre `musica.cifra`. A tag `seqs_famosas` deixa de ser usada para busca, mas continua sendo carregada em `main.py:63` e exposta por `/musicas` e `/musica/<id>` para não quebrar o contrato existente.
  - **API:** `GET /sequencias` e `POST /sequencias` iguais em espírito à Proposta 1, mas sem campo de modo. `/similares` aceita `sequencia_id` e mantém `sequencia=...`; a resolução da string legada concatenada (`BmGDA`) precisa de um mapa de compatibilidade ou de uma coluna `chave_legada`.
  - **Frontend:** mesma mudança da Proposta 1: `sequencia.js` deixa de ter as 4 hardcoded, carrega o catálogo do backend, adiciona formulário e busca por `sequencia_id`/lista de acordes.
  - **Deploy:** mesma estratégia de volume em `/app/instance`; sem novas dependências.
  - **Testes:** a suíte pode reaproveitar `validate_matching.py` como oráculo; o teste de regressão compara os IDs calculados com a fixture dourada.

- **Trade-offs:**
  - **Prós:** uma única regra de matching; catálogo uniforme; nenhuma dependência da tag `SEQ_FAMOSA` para busca; regressão exata comprovada; implementação e testes mais simples; mais fácil explicar “toda sequência funciona do mesmo jeito”.
  - **Contras:** a regra histórica é muito restritiva e provavelmente surpreendente para o usuário. `C-G` retorna 20 músicas, não 11.877; `C-G-Am` retorna 28, não 2.571; `Em-G` retorna apenas 4. Qualquer música com um acorde fora da sequência é descartada. O catálogo novo pode parecer “quebrado” mesmo estando correto pela definição.
  - **Performance:** o critério estrito exige varredura e comparação de sublistas em ~59 mil músicas por requisição. Pode ser aceitável localmente, mas precisa de benchmark; cache por sequência ou índice de n-gramas pode ser necessário.
  - **Produto:** atende à letra do requisito, mas não necessariamente à expectativa de “a sequência aparece na música”. É a opção mais conservadora e menos arriscada tecnicamente, porém a de pior UX para sequências novas.

- **Validation:**
  - **Regressão obrigatória:** rodar `validate_matching.py` e exigir `equal=True` para as 6; depois, via `Flask.test_client`, comparar IDs por página com a fixture dourada, nas formas concatenada e separada por vírgulas.
  - **Semântica estrita:** documentar e testar os números esperados para novas sequências (`C-G` → 20; `C-G-Am` → 28; `Am-F-C-G` → 278). Testar que uma música com acorde extra não aparece, mesmo contendo a sequência contígua.
  - **API/persistência/frontend:** mesmos testes da Proposta 1, sem o campo `match_mode`.
  - **Performance:** benchmark de `/similares?sequencia_id=<id>` para uma sequência curta e uma longa; comparar com o endpoint legado atual. Medir p95 e memória.
  - **Edge cases:** sequência maior que a cifra, cifra vazia, acordes repetidos, acordes com barra/extensão, espaços e maiúsculas/minúsculas.

- **Open Questions:**
  - A semântica estrita é aceitável para o produto? Se não, esta proposta deve ser descartada em favor da Proposta 1 ou de uma variante “contígua para todos, com override legado para as 6”.
  - Vale construir um índice de n-gramas no startup para evitar varredura por requisição?
  - A tag `SEQ_FAMOSA` deve ser removida do CSV/API no futuro ou permanece por compatibilidade?
  - Duplicatas, limites, acordes desconhecidos e moderação continuam em aberto, como na Proposta 1.
  - Normalização de acordes e transposição: fora do escopo ou requisito futuro?

---

## Escopo da Proposta 2 (escolhida)

### Dentro do escopo

1. **Catálogo em SQLite:** novo `db.py` com `sqlite3` (stdlib), banco em `instance/deciframe.db` (override por `DECIFRAME_DB`), tabela `sequencias(id, nome, acordes_json, chave UNIQUE, criado_em)`, criada de forma idempotente. As 6 originais são seedadas de `data/mapeamento_sequencias_famosas.txt` como linhas normais, sem `legacy_id` e sem `match_mode`.
2. **Matching único:** `set(cifra) <= set(seq) and contiguous(cifra, seq)` aplicado sobre `musica.cifra` (a cifra ordenada, não `musica.acordes`), substituindo `get_similares_por_sequencia` (`main.py:203-223`). Ordem importa, repetição interna quebra a adjacência, comparação token a token e case-sensitive.
3. **API:** `GET /sequencias` e `POST /sequencias` (`{"nome": "...", "acordes": ["C","G","Am"]}`), ambos com `json.dumps(...)`. `/similares` ganha `sequencia_id` e mantém `sequencia=` nas duas formas atuais (`BmGDA` e `Bm,G,D,A`) via mapa de compatibilidade. `400` para payload inválido, `409` para duplicata de `chave`; resposta e paginação de 100 iguais a `main.py:210-220`.
4. **Frontend `#/porsequencia`:** `sequencia.js:2-37` deixa de ter as 4 hardcoded e carrega `GET /sequencias`; formulário de cadastro (nome + acordes) com `POST` e recarga do catálogo; busca por `sequencia_id`; correção do `ng-hide="music.diferenca.length"` inócuo em `sequencia.html:41-43`.
5. **Infra e testes:** volume nomeado em `/app/instance`, `instance/` e `*.db` no `.gitignore`/`.dockerignore`; `Dockerfile` e `requirements.txt` sem mudança estrutural nem dependência nova; `tests/` com `unittest` + `Flask.test_client`, banco temporário via `DECIFRAME_DB` e fixture dourada das 6.

### Fora do escopo (não alterado)

1. **CSV em memória:** `data/top/dataset_final.csv`, o loop de carga em `main.py:49-98`, `musicas`, `musicas_dict`, `genero_musicas`, `generos` e `acordes` ficam intactos; `musica.py` não muda.
2. **Tag `SEQ_FAMOSA`:** continua sendo lida em `main.py:63` e exposta por `/musicas` e `/musica/<id>`; ela só deixa de ser usada para busca. O CSV não é regenerado e `scripts/generate_data_set.py` não muda.
3. **Contrato HTTP:** `/search`, `/musicas`, `/musica/<id>/`, `/generos`, `/acordes`, `/`, o proxy de estáticos, o CORS de `add_header` (`main.py:274-277`), o `json.dumps(...)` e o `Content-Type: text/html` continuam iguais; a busca por `acordes=`/`id_unico_musica=` (`get_similares`, `apply_filtro`, `get_pagina`, `TAM_PAGINA = 100`) também.
4. **Produto:** sem normalização ou transposição de acordes (lowercase, enarmonia `C#`/`Db`, acorde com barra, transposição por tom), sem login/moderação/rate limit, sem edição ou exclusão de sequências e sem paginação do catálogo no frontend.
5. **Plataforma:** AngularJS 1.4.9 + jQuery seguem, sem build step; deploy continua o container único local-only do ADR 0001, sem nuvem nem múltiplas instâncias. Índice de n-gramas/cache de resultados só entra se o benchmark exigir.
