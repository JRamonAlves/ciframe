# Plano — Sequências de Acordes Customizadas

## Passos

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
| `static/assets/js/controllers/sequencia.js` | Catálogo via API, busca por `sequencia_id`, formulário/POST, erros |
| `static/templates/sequencia.html` | Formulário de cadastro, mensagem de erro, remoção do `ng-hide` inócuo |
| `tests/test_sequencias.py` (novo) | Suíte `unittest` + `Flask.test_client` com banco temporário |
| `tests/fixtures/sequencias_originais.json` (novo) | Fixture dourada dos IDs das 6, capturada antes da mudança |
| `.gitignore`, `.dockerignore` | `instance/`, `*.db` |
| `README.md` | Comando Docker com volume nomeado (seção “Rodando localmente”) e consequência de não usar volume |

## Riscos e mitigação

Sobre testes: 
- **Oráculo de matching:** `validate_matching.py` continua sendo a prova de que o critério estrito reproduz a tag (`equal=True` para as 6); a suíte de API prova que o roteamento por id/string cai no mesmo cálculo.
- **Regressão:** comparação de **listas exatas de IDs** (não só contagem) contra a fixture capturada no passo 1, nas duas formas de string e via `sequencia_id`, com e sem gênero, percorrendo todas as páginas.
- **Semântica:** `C-G` → 20; `C-G-Am` → 28; `Am-F-C-G` → 278; ordem importa; repetição quebra adjacência; acorde extra na música exclui o match.
- **Comando:** `python3 -m unittest discover -s tests -v` a partir da raiz. A suíte carrega o CSV (~alguns segundos) uma vez por processo; é esperado.

Sobre a segurança, influi apenas na escrita anônima: limites de tamanho (nome, quantidade/tamanho de acordes, `MAX_CONTENT_LENGTH`) e rejeição de delimitadores evitam payloads abusivos e corrupção da `chave`. Sem autenticação, moderação ou rate limit — catálogo aberto é requisito explícito, e moderação está fora do escopo.

Mais riscos:
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
