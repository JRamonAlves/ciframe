# Plano — Sequências de Acordes Customizadas (Proposta 2)

> Documento de apoio à fase 03. Ele detalha a execução da Proposta 2 e não
> substitui `../03-plan.md`, que continua sendo o template oficial da fase.
> Escopo fixado em [`../02-proposal.md`](../02-proposal.md): catálogo em SQLite
> com **matching estrito uniforme**. Sem prazo definido pelo solicitante; a ordem
> abaixo é a ordem de dependência de execução. Nenhum código é alterado nesta
> fase.

## Contexto atual

- `main.py` carrega `data/top/dataset_final.csv` no import (67.585 músicas, 52 gêneros, 6.653 tokens de acorde). Cada `Musica` tem `cifra` (lista ordenada), `acordes` (`list(set(cifra))`) e `seqs_famosas` (tag do CSV).
- As 6 sequências originais vivem em um dict hardcoded (`main.py:40-45`); a busca por sequência só resolve a string concatenada (`BmGDA`) e delega a `get_similares_por_sequencia` (`main.py:203-223`), que apenas checa `str(id_seq) in musica.seqs_famosas`.
- Não há cálculo em tempo real, nem escrita, nem catálogo persistido. SQLite é stdlib e cabe no container único do ADR 0001, mas não há volume: hoje o banco em `/app/instance` morreria em `docker rm`.
- Frontend (`#/porsequencia`) tem 4 sequências hardcoded em `sequencia.js:2-37` (IDs 0, 1, 4, 5), monta `similares?sequencia=<acordes com vírgula>` e não tem formulário, validação nem tratamento de erro.
- Evidência empírica (`validate_matching.py`): o critério `set(cifra) <= set(seq) and contiguous(cifra, seq)` reproduz exatamente as tags das 6 (`199, 296, 4, 5, 7, 3` músicas), com 0 faltantes e 0 extras.
- `instance/` e `*.db` não estão em `.gitignore`/`.dockerignore` (`.gitignore` = `static/assets/vendor`, `.venv`, `*.pyc`, `__pycache__/`; `.dockerignore` = `.git`, `.venv`, `__pycache__`, `*.pyc`).

## Requisitos

- Qualquer visitante cadastra sequência (nome + lista ordenada de acordes) sem login, e busca músicas por qualquer sequência do catálogo.
- Catálogo persistido em banco e sobrevivendo a restart do container (com volume nomeado).
- Regressão obrigatória: as 6 originais retornam **os mesmos IDs, na mesma ordem e com a mesma paginação** de antes.
- Frontend `#/porsequencia` carrega o catálogo do backend e permite cadastrar.
- Contrato preservado: `json.dumps(...)` (nunca `jsonify`), `Content-Type: text/html`, `TAM_PAGINA = 100`, filtro `generos`, aceitação de `sequencia=` nas duas formas atuais, e os demais endpoints (`/search`, `/musicas`, `/musica/<id>/`, `/generos`, `/acordes`, estáticos, CORS) intocados.
- Sem dependência nova (`requirements.txt` inalterado), sem serviço externo, container único.

## Decisões de design

- **Matching único (estrito):** `set(cifra) <= set(seq) and contiguous(cifra, seq)`, sobre `musica.cifra` (ordenada). Token a token, case-sensitive, sem normalização; repetição interna quebra adjacência; sequência maior que a cifra nunca casa. Nada muda em `musica.py`.
- **Banco:** `sqlite3` da stdlib em `db.py`; caminho `DECIFRAME_DB` ou `app.instance_path/deciframe.db`; `os.makedirs(instance_path, exist_ok=True)`; `PRAGMA journal_mode=WAL` e `busy_timeout=5000`; conexão por operação com context manager (gunicorn roda 1 worker, então sem pool).
- **Schema:** `sequencias(id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, acordes_json TEXT NOT NULL, chave TEXT NOT NULL UNIQUE, criado_em TEXT NOT NULL)`. `chave = ','.join(acordes)` — a posição importa, então não ordenar; duplicata é a mesma lista na mesma ordem.
- **Seed:** as 6 originais entram como linhas normais com IDs explícitos `0..5`, via `INSERT OR IGNORE` (idempotente, sem `legacy_id`/`match_mode`), a partir de constantes em `db.py` espelhadas de `data/mapeamento_sequencias_famosas.txt` (nomes e acordes `Bm-G-D-A`, `C-G-Am-F`, `Em-G`, `C-A7-Dm-G7`, `Gm-F`, `C-C7-F-Fm`).
- **Compatibilidade da string legada:** a concatenação (`BmGDA`, `CGAmF`, `CA7DmG7`, `CC7FFm`) não é tokenizável de volta em geral, então `db.py` mantém `LEGACY_STRINGS = {'BmGDA': 0, ...}` apenas para as 6. Resolução de `sequencia=` em ordem: (1) `seq.replace(',', '')` no mapa legado; (2) `seq` como `chave` do catálogo (cobre sequências novas em forma `C,G,Am`); (3) nada encontrado → `404 {"erro": ...}`.
- **API:**
  - `GET /sequencias` → `200` com `[{id, nome, acordes: [...], criado_em}]` ordenado por `id` (6 seeds primeiro).
  - `POST /sequencias` → `201` com o objeto criado; `400` para JSON inválido/payload inválido; `409` com `{"erro": ..., "id": <existente>}` para `chave` duplicada.
  - `/similares?sequencia_id=<id>` novo; `sequencia=` mantido; `sequencia_id` inexistente → `404`. Resposta do caminho de sequência mantém as chaves atuais (`id_unico_musica`, `id_artista`, `id_musica`, `nome_artista`, `nome_musica`, `popularidade`, `acordes`, `genero`, `url`) e a ordem de `musicas` filtrada por gênero, paginada com `get_pagina`.
  - Precedência de parâmetros em `/similares` inalterada: `acordes` > `id_unico_musica` > sequência.
- **Validação do POST:** `nome` string não vazia após `strip`, ≤ 120 chars; `acordes` lista de 1..32 strings não vazias após `strip`, cada uma ≤ 16 chars; rejeitar `,` `;` `|` dentro de um acorde (são delimitadores legados); `app.config['MAX_CONTENT_LENGTH'] = 16 * 1024` como teto de payload. Sem dedupe: repetição é permitida e significativa.
- **Frontend:** `sequencia.js` perde as 4 hardcoded e chama `GET sequencias` no init; converte `acordes: ["C","G"]` em `[{acorde, cor: '#2E1C74'}]` para reutilizar `df-hex` sem tocar na diretiva. Busca passa a usar `sequencia_id`; formulário (`ng-submit`) com nome e acordes separados por vírgula faz `POST`, exibe erro de `400`/`409`, recarrega o catálogo e limpa o formulário. `sequencia.html`: bloco do formulário no painel esquerdo e remoção do `ng-hide="music.diferenca.length"` (no-op, pois a resposta de sequência não tem `diferenca`).
- **Deploy:** volume nomeado em `/app/instance` (`docker run -v ciframe-instance:/app/instance -p 8080:8080 ciframe`), nunca em `/app/data` (esconderia o CSV). `instance/` e `*.db` em ambos os ignores. `Dockerfile` e `requirements.txt` sem mudança estrutural.
- **Fora do escopo (decidido não fazer):** normalização/transposição (case, enarmonia, barra, tom), edição/exclusão de sequências, moderação/rate limit/login, paginação do catálogo, índice de n-gramas/cache (só se o benchmark exigir), migração das músicas para o banco, remoção da tag `SEQ_FAMOSA`.

## Plano de implementação

1. [ ] Subir o app atual (`python main.py`) para capturar a linha de base.
2. [ ] Capturar IDs por página das 6 (forma concatenada e com vírgulas, com e sem `generos=Rock`) em `tests/fixtures/sequencias_originais.json`.
3. [ ] Rodar `validate_matching.py` e anotar as 6 contagens esperadas.
4. [ ] Criar `db.py` com path via `DECIFRAME_DB`, `init_db()`, WAL e `busy_timeout`.
5. [ ] Criar a tabela `sequencias(id, nome, acordes_json, chave UNIQUE, criado_em)`.
6. [ ] Seed idempotente das 6 originais (IDs 0..5) com `INSERT OR IGNORE`.
7. [ ] Implementar `listar_sequencias()`, `criar_sequencia()`, `buscar_por_id()` e `buscar_por_chave()`.
8. [ ] Adicionar `LEGACY_STRINGS` e `resolver_sequencia_legada()` para as 6 concatenações.
9. [ ] Chamar `init_db()` no import de `main.py` e remover o dict `sequencias`.
10. [ ] Implementar `sequencia_contigua(cifra, seq)` com o critério estrito.
11. [ ] Reescrever `get_similares_por_sequencia(acordes_seq, generos_key)` sobre `musica.cifra`.
12. [ ] Aceitar `sequencia_id` em `/similares`, mantendo `sequencia=` e a precedência dos parâmetros.
13. [ ] Resolver `sequencia`/`sequencia_id` para acordes e retornar 404 se não existir.
14. [ ] Implementar `GET /sequencias` ordenado por id, com `json.dumps`.
15. [ ] Implementar `POST /sequencias` com validação, 201/400/409 e `MAX_CONTENT_LENGTH`.
16. [ ] Trocar as 4 hardcoded de `sequencia.js` por `GET sequencias` no init.
17. [ ] Buscar por `sequencia_id` e mapear acordes para `{acorde, cor}` no controller.
18. [ ] Adicionar `cadastrarSequencia()` no controller, com erro, POST e recarga do catálogo.
19. [ ] Adicionar formulário e mensagem de erro em `sequencia.html` e remover o `ng-hide` inócuo.
20. [ ] Adicionar `instance/` e `*.db` a `.gitignore` e `.dockerignore`.
21. [ ] Documentar no README o `docker run -v ciframe-instance:/app/instance`.
22. [ ] Criar `tests/test_sequencias.py` com `DECIFRAME_DB` temporário e import de `main` em `setUpModule`.
23. [ ] Testar regressão exata das 6 contra a fixture (3 formas, com e sem gênero).
24. [ ] Testar catálogo: 6 seeds, POST 201, 409, 400 e 404.
25. [ ] Testar matching estrito (`C-G` → 20), paginação, filtro e `Content-Type`.
26. [ ] Medir p95 de `/similares?sequencia_id=` (curta e longa) contra o legado.
27. [ ] Verificar persistência após `docker restart` e após `docker rm` + `docker run` com volume.
28. [ ] Rodar checklist E2E no browser (6 na lista, cadastro, busca, gênero, reload, erros).

## Arquivos afetados

| Arquivo | Mudança |
|---|---|
| `db.py` (novo) | Conexão SQLite, schema, seed idempotente, CRUD do catálogo, mapa de compatibilidade legado |
| `main.py` | `init_db()`, remoção do dict `sequencias`, matching estrito, `/sequencias` GET/POST, `sequencia_id` em `/similares` |
| `musica.py` | Sem mudança |
| `static/assets/js/controllers/sequencia.js` | Catálogo via API, busca por `sequencia_id`, formulário/POST, erros |
| `static/templates/sequencia.html` | Formulário de cadastro, mensagem de erro, remoção do `ng-hide` inócuo |
| `tests/test_sequencias.py` (novo) | Suíte `unittest` + `Flask.test_client` com banco temporário |
| `tests/fixtures/sequencias_originais.json` (novo) | Fixture dourada dos IDs das 6, capturada antes da mudança |
| `.gitignore`, `.dockerignore` | `instance/`, `*.db` |
| `README.md` | Comando Docker com volume nomeado (seção “Rodando localmente”) e consequência de não usar volume |
| `Dockerfile`, `requirements.txt`, `static/assets/js/routes.js`, `static/assets/js/directives/df-hex.js`, `data/`, `scripts/` | Sem mudança |

## Testes

- **Oráculo de matching:** `validate_matching.py` continua sendo a prova de que o critério estrito reproduz a tag (`equal=True` para as 6); a suíte de API prova que o roteamento por id/string cai no mesmo cálculo.
- **Regressão:** comparação de **listas exatas de IDs** (não só contagem) contra a fixture capturada no passo 1, nas duas formas de string e via `sequencia_id`, com e sem gênero, percorrendo todas as páginas.
- **Semântica:** `C-G` → 20; `C-G-Am` → 28; `Am-F-C-G` → 278; ordem importa; repetição quebra adjacência; acorde extra na música exclui o match.
- **Comando:** `python3 -m unittest discover -s tests -v` a partir da raiz. A suíte carrega o CSV (~alguns segundos) uma vez por processo; é esperado.

## Observabilidade

Não se aplica: o projeto não tem infraestrutura de logs/métricas além do log padrão do gunicorn/Flask, e a feature não exige nenhuma. Nenhuma mudança necessária.

## Rollout

Local-only, sem deploy remoto (ADR 0001). Rollout = rebuild da imagem + `docker run` com o volume nomeado. Banco é criado e seedado no primeiro boot; reinícios não duplicam seeds (`INSERT OR IGNORE`). Reverter = voltar a imagem anterior com o mesmo volume (o schema novo é ignorado pelo código antigo, que não lê o banco).

## Segurança

Influi apenas na escrita anônima: limites de tamanho (nome, quantidade/tamanho de acordes, `MAX_CONTENT_LENGTH`) e rejeição de delimitadores evitam payloads abusivos e corrupção da `chave`. Sem autenticação, moderação ou rate limit — catálogo aberto é requisito explícito, e moderação está fora do escopo.

## Riscos e mitigação

- **Regressão silenciosa nas 6:** a fixture precisa ser capturada **antes** do passo 2; sem ela não há como provar igualdade de IDs. Mitigação: passo 1 obrigatório + teste de lista exata.
- **Semântica estrita surpreende o usuário** (`C-G` rende 20 músicas, não 11.877): decisão de produto já registrada na Proposta 2. Mitigação: documentar no ADR/README e não prometer cobertura ampla na UI.
- **Performance:** varredura de ~67 mil cifras por request e gunicorn com 1 worker (request bloqueia o worker). Mitigação: `apply_filtro` antes do loop, checagem de conjunto barata, benchmark no passo 9; cache/índice apenas se estourar o critério.
- **404 para sequência desconhecida muda o contrato atual** (hoje `[]`): clientes que mandavam string inválida passam a ver erro. Mitigação: decisão consciente e documentada; a UI trata o erro e não envia strings arbitrárias (busca por `sequencia_id`).
- **String legada ambígua:** concatenação não é reversível (`CA7DmG7`) e não existe para sequências novas. Mitigação: mapa fixo das 6; forma com vírgulas resolve pelo catálogo; concatenado de sequência nova retorna `404` documentado.
- **SQLite no container:** sem volume, `docker rm` apaga o catálogo; arquivos `-wal`/`-shm` vivem no mesmo diretório. Mitigação: volume em `/app/instance` documentado no README e ignores corretos.
- **Concorrência/DB lock:** baixa no cenário local (1 worker), mas `POST` e `GET` concorrentes ainda tocam o arquivo. Mitigação: WAL + `busy_timeout`.
- **Teste frágil por import do CSV:** `main.py` carrega 67 mil linhas no import. Mitigação: `DECIFRAME_DB` definido antes do import (import dentro de `setUpModule`) e uma única carga por processo.

## Definição de pronto

- [ ] Qualquer pessoa cadastra uma sequência (nome + acordes) pela UI e via `POST /sequencias` (`201`), e ela aparece em `GET /sequencias` após reload.
- [ ] Buscar por uma sequência cadastrada (`sequencia_id` e forma com vírgulas) retorna músicas pelo critério estrito, com paginação de 100 e filtro de gênero.
- [ ] As 6 originais retornam exatamente os mesmos IDs da fixture, nas duas formas de string e via `sequencia_id`, com e sem gênero.
- [ ] `400`/`409`/`404` se comportam como decidido; `json.dumps` e `Content-Type: text/html` preservados.
- [ ] Catálogo sobrevive a reinício do processo e a `docker restart` com volume nomeado; `instance/` e `*.db` ignorados.
- [ ] Suíte `python3 -m unittest discover -s tests -v` verde; benchmark dentro do critério ou plano atualizado com a mitigação escolhida.
