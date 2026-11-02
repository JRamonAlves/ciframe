# Relatório de testes — Sequências de Acordes Customizadas

## Cobertura

tests/test_sequencias.py tem 15 testes (unittest), todos passando. Rodei agora com .venv/bin/python.

TestCatalogo
- test_seis_originais_na_ordem: GET /sequencias devolve as 6 originais (seed) na ordem e com os ids esperados.
- test_post_201_e_aparece_na_listagem: um POST válido retorna 201 e a sequência aparece na listagem.
- test_repeticao_interna_e_permitida: aceita acordes repetidos dentro de uma mesma sequência.
- test_409_para_chave_duplicada: uma sequência duplicada retorna 409.
- test_400_para_payload_invalido: vários payloads inválidos retornam 400.
- test_413_para_payload_acima_do_limite: payload grande demais retorna 413.
- test_endpoints_existentes_mantem_contrato: os endpoints antigos, como /generos, continuam com o mesmo contrato.

TestBuscaPorSequencia
- test_matching_estrito_unitario: testa o matching estrito sobre a cifra.
- test_contagens_da_semantica_estrita: confere as contagens de resultados da semântica estrita.
- test_ordem_dos_acordes_muda_o_resultado: uma ordem diferente dos acordes gera um resultado diferente.
- test_paginacao_e_filtro_de_genero: confere a paginação e o filtro por gênero.
- test_sequencia_inexistente_retorna_404: um sequencia_id inexistente retorna 404.
- test_concatenacao_so_resolve_as_seis_originais: a forma concatenada (BmGDA) só resolve as 6 originais.
- test_precedencia_dos_parametros: define qual parâmetro vence quando vários são enviados.

TestRegressaoSequenciasOriginais
- test_regressao_das_seis: descrito abaixo.

## Teste de regressão obrigatório

A fixture tests/fixtures/sequencias_originais.json guarda as respostas das 6 sequências originais capturadas do main.py antes da migração para o SQLite. Para cada uma das 6, o teste test_regressao_das_seis chama /similares de 3 formas:
- sequencia concatenada (BmGDA);
- sequencia com vírgulas (Bm,G,D,A);
- sequencia_id.

Cada forma é testada com gênero Rock, com Samba e sem gênero. Ele compara lista, ordem e paginação com a fixture, página por página.

Sem generos, a ordem depende da iteração de um set, que não é determinística entre processos, nem no código antigo. Por isso o teste reaplica a ordem de gêneros gravada na fixture, trocando main.generos temporariamente, e compara as páginas exatas.

Resultado: passou (ok) para as 6 sequências, nas 3 formas de chamada e nos 3 cenários de gênero.

## Como rodar

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest tests.test_sequencias -v
```

## O que ficou de fora

Pedi pra outra sessão revisar o trabalho feito pela sessão que implementou o trabalho inteiro. Ele encontrou muitos erros, mas eu decidi genuinamente ignorar, exceto uma que percebi durante o teste manual (relacionadoa a uma guarda do frontend). Testei a UI, parecia esta bem funciona. Li o arquivo de testes, li o arquivos que ele alterou e nada estava fora de propósito ou não seguido algo que eu não faria se eu fosse contribuir com o repositório. Não reflete necessariamente o que eu faria se eu realmente quisesse contribuir, muito provavalmente eu iria mais pra uma linha de garantir coisas antes, abriria outras PRs antes, inicialmente criando CIs, criando mais testes automáticos, adicionaria também testes relacionados a angular, etc etc. Nesse contexto, eu estou feliz com a implementação feita, foi dentro do esperado na minha opinião.
