# Proposta — Sequências de Acordes Customizadas

## Abordagem escolhida

### Algoritmo de matching

Todas as sequências, incluindo as 6 originais, usam a mesma regra calculada em tempo real: a sequência é uma sublista contígua da cifra e todos os acordes da música pertencem ao conjunto da sequência (set(cifra) <= set(seq) and contiguous(cifra, seq)). Esse trecho foi retirado direto do proposal que ele escreveu, descreve bem como vai funcionar o algoritmo. 

### Banco de dados

SQLite, fácil de implementar e pertence a linguagem como stdlib, não aumenta o requiriments.txt.

### Esquema de dados (alto nível)

(id, nome, acordes_json, chave UNIQUE, criado_em). Também tirado direto do proposal gerado por ele.

### API

GET /sequencias e POST /sequencias. Também tirados direto do proposal.

### Frontend

Em static/assets/js/controllers/sequencia.js:2-37, remover as 4 sequências hardcoded; carregar GET sequencias na inicialização. Adicionar formulário em static/templates/sequencia.html:6-8 com nome e lista de acordes, POST e recarga do catálogo. Trecho retirado direto do proposal gerado por ele. Essa parte faz mais sentido quando se lê todo o resto do proposal. 

## Alternativas consideradas e descartadas

Trocar o algoritmo por um híbrido. Não achei que fizesse muito sentido, achei melhor usar algo mais consistente.

## Escopo explícito

**Dentro do escopo:**

1. Catálogo de sequências em SQLite (db.py, instance/deciframe.db), tabela sequencias(id, nome, acordes_json, chave UNIQUE, criado_em), com as 6 originais seedadas como linhas normais.
2. Matching único set(cifra) <= set(seq) and contiguous(cifra, seq) sobre musica.cifra, substituindo get_similares_por_sequencia.
3. GET /sequencias e POST /sequencias com json.dumps(...); /similares ganha sequencia_id e mantém sequencia= nas duas formas; 400 inválido, 409 duplicata.
4. sequencia.js deixa de ter as 4 hardcoded, carrega o catálogo, ganha formulário de cadastro e busca por sequencia_id.
5. Volume nomeado em /app/instance, ignores atualizados, e tests/ com unittest + test_client e fixture dourada das 6.
Fora do escopo (5 linhas)

**Fora do escopo (e por quê):**

1. CSV de músicas/gêneros e o loop main.py:49-98 (musicas, genero_musicas, generos, acordes) ficam intactos; musica.py não muda.
2. A tag SEQ_FAMOSA continua carregada e exposta em /musicas e /musica/<id>; só deixa de ser usada na busca.
3. /search, /musicas, /musica/<id>/, /generos, /acordes, estáticos, CORS e Content-Type: text/html inalterados; busca por acordes=/id_unico_musica= também.
4. Sem normalização/transposição de acordes, sem login/moderação/rate limit, sem edição ou exclusão de sequências, sem paginação do catálogo.
5. Stack AngularJS/jQuery e Dockerfile/requirements.txt sem mudança estrutural; scripts/ e o CSV não são regenerados; índice/cache e nuvem ficam para depois.
