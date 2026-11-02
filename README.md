# deciframe

Descubra as músicas que você já sabe tocar (e ainda não faz ideia). Busque por
título/artista, gênero, pelos acordes que você já manja, ou por sequências de
acordes famosas — o deciframe cruza isso com uma base de cifras e sugere
músicas parecidas.

Stack: backend Flask (Python) servindo uma API JSON + um frontend AngularJS
estático, numa base de músicas carregada de um CSV em memória e num catálogo de
sequências de acordes persistido em SQLite.

## Rodando localmente

### Com Docker

```
docker build -t ciframe .
docker run -v ciframe-instance:/app/instance -p 8080:8080 ciframe
```

O volume nomeado `ciframe-instance` guarda `/app/instance/deciframe.db`, onde
ficam as sequências cadastradas. Sem o volume, `docker rm` apaga o catálogo
(um novo `docker run` recria apenas as seis sequências originais).

Acesse [http://localhost:8080](http://localhost:8080).

### Com virtualenv

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Acesse [http://localhost:5000](http://localhost:5000).

O banco fica em `instance/deciframe.db` (ou no caminho de `DECIFRAME_DB`).

### Busca por sequência

A busca usa um critério estrito: todos os acordes da música precisam pertencer
à sequência, e a sequência precisa aparecer em ordem contígua na cifra. Por
isso uma sequência curta costuma retornar bem menos músicas do que uma busca
por conjunto de acordes.

---

Para convenções de contribuição, veja [CONTRIB.md](CONTRIB.md). Licença: [LICENSE](LICENSE).
