# Pesquisa — Sequências de Acordes Customizadas

## Perguntas que você precisa responder

1. **Algoritmo de matching**: hoje, as 6 sequências hardcoded em `main.py` (linhas
   40-45) são comparadas contra músicas via uma tag pré-computada
   (`SEQ_FAMOSA`/`seqs_famosas`, vinda do CSV). Sequências cadastradas pelo usuário
   não têm essa tag — o matching precisa ser calculado em tempo real a partir da
   lista de acordes de cada música (`musica.acordes`/`musica.cifra`). O que vai
   definir "a sequência X aparece na música Y"? A ordem dos acordes importa?
   Repetições de acorde dentro da música importam? É preciso normalizar (ex.:
   maiúsculas/minúsculas, variações de escrita do mesmo acorde)?
2. **Validação da hipótese**: rode o algoritmo que você está considerando contra os
   dados reais em `data/top/dataset_final.csv`, para as 6 sequências hoje
   hardcoded, e confirme (ou refute) que ele reproduz os mesmos matches que o
   código atual produz via `seqs_famosas`. Esse é o bar mínimo de correção que
   você vai usar na fase de testes.
3. **Banco de dados**: quais bancos embarcados (sem serviço externo adicional) são
   viáveis dentro do container Docker único e local-only já documentado em
   `docs/adr/0001-local-only-docker-deploy.md`? O que cada opção implica para o
   `Dockerfile` atual e para a persistência dos dados entre reinícios do
   container?
4. **Frontend existente**: o que a página `#/porsequencia`
   (`static/templates/sequencia.html` +
   `static/assets/js/controllers/sequencia.js`) já faz? Repare que ela tem hoje uma
   lista *hardcoded no JavaScript* de 4 sequências (`sequencia1`..`sequencia4`),
   diferente das 6 que existem no backend — um detalhe real e pré-existente do
   código, não um erro seu, que vale entender antes de decidir o que precisa
   mudar.

## Registro das descobertas

Antes de responder acho que a primeira coisa que notei foi que nessa configuração (framework + harness + modelo), pelo menos a fase de pesquisa, tudo fica muito preto no branco, o modelo não da sugestão de nada. Ele fez 2 documentos, eu pedi 2 um geral e um específico pra a task, e ele me deu 2 arquiteturas, bastante verborrágicas e meio confusas. Do que eu li, as descobertas incluem muito sobre as tecnologias, arquivos usados, como funcionam as comunicações dos modulos (front -> back -> banco) e o que cada um é. 
Sobre sobre o algoritmo de matching, ele falou sobre como funciona, como estão armazenadas as músicas (em csv), como é feita a pesquisa, bem detalhado mesmo. Esta tudo registrado na pesquisa. Esse ponto realmente ele se foi bem exitoso. Hoje o runtime não compara acordes: só verifica str(id_seq) in musica.seqs_famosas (main.py:209). A tag foi gerada por scripts/generate_data_set.py:7-24 com um critério mais restrito: a sequência aparece contígua na cifra e todo acorde da música pertence ao conjunto da sequência (set(cifra) ⊆ set(sequência)). Ordem importa; repetição interna quebra a adjacência; usar musica.cifra (ordenada), não musica.acordes (set). Não baixar para minúsculas: AM7 ≠ Am7, DM7 ≠ Dm7; enarmônicos e acordes com barra também são tokens distintos.
Eu pedi pra ele validar em outra sessão e eu fui validando por fora também e no final isso só confundiu ele. Rodei o matching em tempo real contra o CSV (67.585 músicas). O critério legado — set(cifra) ⊆ set(sequência) e sequência contígua — reproduz exatamente as 6 tags: 199 / 296 / 4 / 5 / 7 / 3, com 0 faltantes e 0 extras. O contíguo simples retorna 866 / 1.216 / 3.110 / 96 / 1.039 / 132: não perde nenhuma da tag, mas adiciona centenas/milhares. Exemplo: bon-jovi_bells-of-freedom tem Bm G D A, mas também Bm/A, então só casa no contíguo. Script: generated/validate_matching.py.
SQLite é viável sem serviço externo e sem dependência nova (sqlite3 é stdlib; confirmado no python:3.9-slim). TinyDB e JSON próprio também são viáveis, mas perdem transações/concorrência; DuckDB é overkill; PostgreSQL/MySQL violam o ADR 0001. No Docker atual, o banco em /app/instance sobrevive a docker restart, mas não a docker rm + docker run novo, porque não há volume. Para persistência real: volume nomeado (-v deciframe-data:/app/instance) e excluir instance/ e *.db do .dockerignore.
Sobre o frontend, a página lista 4 sequências hardcoded (sequencia.js:2-37), correspondentes aos IDs 0, 1, 4 e 5; faltam EmG (2) e CA7DmG7 (3). Ela monta similares?sequencia=..., filtra por gênero e renderiza os resultados, mas não busca catálogo no backend, não tem formulário/POST, não valida, não trata loading/erro e não pagina. O ng-hide="music.diferenca.length" é no-op porque a resposta de sequência não tem diferenca. 

## Trade-offs identificados

Sobre o algoritmo: legado (regressão exata, mas restritivo) vs contíguo (intuitivo, mas muda as 6) vs híbrido (preserva as 6 e usa semântica nova para as novas).
Sobre o banco: SQLite (melhor encaixe, stdlib e local-only) vs TinyDB/JSON (simples, menos garantias); volume nomeado vs bind mount.
Sobre o front: catálogo backend-driven vs hardcoded; formulário inline vs modal; lista de acordes vs sequencia_id; rejeitar vs permitir duplicatas.
