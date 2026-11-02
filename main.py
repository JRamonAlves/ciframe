# coding: utf-8
import json
from flask import Flask, request
import sys
from musica import *
from collections import OrderedDict
import unicodedata
import db

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024
db.init_db(app.instance_path)

def limpa_cifra(raw_cifra):
    cifra = []
    for m in raw_cifra:
        if m.strip() != '':
            # filtra tablaturas
            if '|' in m:
                acorde = m.split('|')[0].split()[0]
                cifra.append(acorde)
            # lida com acordes separados por espaço
            else:
                tokens = [token for token in m.split()]
                cifra += tokens
    return cifra

# colunas do csv
ARTISTA_ID = 0
MUSICA_ID = 1
ARTISTA = 2
MUSICA = 3
GENERO = 4
POPULARIDADE = 5
TOM = 6
SEQ_FAMOSA = 7
CIFRA = 8
TAM_PAGINA = 100
NOME_MAX = 120
ACORDES_MAX = 32
ACORDE_MAX = 16
DELIMITADORES = (',', ';', '|')

genero_musicas = {}
generos = set()
acordes = set()

musicas_dict = {}

f = open('data/top/dataset_final.csv')
f.readline()

for line in f:
    line = line.replace('"', '').replace('NA', '')[:-1]

    musica = line.split(',')
    musica[POPULARIDADE] = int(musica[POPULARIDADE].replace('.', ''))

    if musica[CIFRA] != '':
        musica[CIFRA] = limpa_cifra(musica[CIFRA].split(';'))
    else:
        musica[CIFRA] = []

    musica[SEQ_FAMOSA] = musica[SEQ_FAMOSA].split(";")

    # conjunto único de gêneros
    generos.add(musica[GENERO])

    # inclui música no dict de músicas
    musica_obj = Musica(musica[ARTISTA_ID], musica[ARTISTA],
            musica[MUSICA_ID], musica[MUSICA], musica[GENERO],
            int(musica[POPULARIDADE]), musica[SEQ_FAMOSA],
            musica[TOM], musica[CIFRA])

    musicas_dict[musica_obj.id_unico_musica] = musica_obj

    # conjunto único de acordes
    for acorde in musica_obj.acordes:
        acordes.add(acorde)

    # constrói dict mapeando gênero para músicas
    # deve ser usado para melhorar o desempenho das buscas
    if musica_obj.genero in genero_musicas:
        genero_musicas[musica_obj.genero].append(musica_obj)
    else:
        genero_musicas[musica_obj.genero] = [musica_obj]

# dicionário de músicas cujos valores são ordenados por popularidade
musicas = OrderedDict(sorted(musicas_dict.items(),
    key=lambda x: x[1].popularidade, reverse = True))

# para trabalhar melhor com json
generos = list(generos)

# ordena genero_musicas por popularidade
for k,v in genero_musicas.items():
    genero_musicas[k].sort(key = lambda x : x.popularidade, reverse = True)

f.close()


@app.route('/')
def index():
    return app.send_static_file('index.html')
''' Busca por músicas que possuem no título ou no nome do artista o argumento passado por key.
params: key e generos (opcional). Caso generos não sejam definidos, a busca não irá filtrar por gênero.
exemplo 1: /search?key=no dia em que eu saí de casa
exemplo 2: /search?key=no dia em que eu saí de casa&generos=Rock,Samba '''

@app.route('/<path:path>')
def static_proxy(path):
  # send_static_file will guess the correct MIME type
  return app.send_static_file(path)

@app.route('/search')
def busca():
    generos_tag = request.args.get('generos', [])
    pagina_tag = request.args.get('pagina','1')
    keys = request.args.get('key').lower()
    keys = remover_combinantes(keys).split(' ')

    generos_key = generos
    if generos_tag:
        generos_key = generos_tag.split(',')

    collection = apply_filtro(musicas.values(), generos_key)
    out = []

    for musica in collection:
        text = '%s %s' % (musica.nome_artista.lower(), musica.nome_musica.lower())
        text_list = remover_combinantes(text).split(' ')
        if all(key in text_list for key in keys):
            matches = {
                'id_unico_musica' : musica.id_unico_musica,
                'id_artista' : musica.id_artista,
                'id_musica' : musica.id_musica,
                'nome_artista' : musica.nome_artista,
                'nome_musica' : musica.nome_musica,
                'genero' : musica.genero,
                'url' : musica.url,
            }
            out.append(matches)
    return json.dumps(get_pagina(out, pagina_tag))

# cópia
def remover_combinantes(string):
    string = unicodedata.normalize('NFD', string)
    return u''.join(ch for ch in string if unicodedata.category(ch) != 'Mn')

''' Retorna as músicas armazenadas no sistema (ordenados por popularidade).
    O serviço é paginado. Cada página tem tamanho 100, por default.
    params: pagina. Caso não seja definida a página, o valor default é 1.
    exemplo 1: /musica?pagina=2
    exemplo 2: /musica'''
@app.route('/musicas')
def get_musicas():
    return json.dumps([v.__dict__ for v in musicas.values()])

@app.route('/generos')
def get_generos():
    return json.dumps(generos)

@app.route('/acordes')
def get_acordes():
    return json.dumps(list(acordes))

@app.route('/sequencias', methods=['GET'])
def get_sequencias():
    return json.dumps(db.listar_sequencias())

@app.route('/sequencias', methods=['POST'])
def post_sequencia():
    payload = request.get_json(silent=True)

    try:
        nome, acordes_seq = validar_sequencia(payload)
    except ValueError as erro:
        return json.dumps({'erro': str(erro)}), 400

    try:
        sequencia = db.criar_sequencia(nome, acordes_seq)
    except db.SequenciaDuplicada as erro:
        return json.dumps({
            'erro': 'Sequência já cadastrada.',
            'id': erro.id_existente,
        }), 409

    return json.dumps(sequencia), 201

@app.route('/musica/<m_id>/')
def get_musica(m_id):
    return json.dumps(musicas[m_id].__dict__)

@app.route('/similares')
def get_similares():
    # tratando request
    acordes_tag = request.args.get('acordes')
    id_musica_tag = request.args.get('id_unico_musica')
    sequencia_tag = request.args.get('sequencia')
    sequencia_id_tag = request.args.get('sequencia_id')
    pagina_tag = request.args.get('pagina','1')

    # se não existir, filtra por todos.
    generos_tag = request.args.get('generos')
    generos_key = generos
    if generos_tag:
        generos_key = generos_tag.split(',')

    acordes = []
    if acordes_tag:
        acordes = acordes_tag.split(',')
    elif id_musica_tag:
        musica = musicas[id_musica_tag]
        acordes = musica.acordes
    elif sequencia_id_tag or sequencia_tag:
        sequencia = None

        if sequencia_id_tag:
            try:
                id_seq = int(sequencia_id_tag)
            except (TypeError, ValueError):
                id_seq = None
            if id_seq is not None:
                sequencia = db.buscar_por_id(id_seq)
        else:
            id_seq = db.resolver_sequencia_legada(sequencia_tag)
            if id_seq is not None:
                sequencia = db.buscar_por_id(id_seq)
            if sequencia is None:
                sequencia = db.buscar_por_chave(sequencia_tag)

        if sequencia is None:
            return json.dumps({'erro': 'Sequência não encontrada.'}), 404

        similares = get_similares_por_sequencia(sequencia['acordes'],
                                                generos_key)
        return json.dumps(get_pagina(similares, pagina_tag))

    similares = get_similares(acordes, generos_key, id_musica_tag)

    return json.dumps(get_pagina(similares, pagina_tag))

def sequencia_contigua(cifra, seq, acordes_musica=None, conjunto_seq=None):
    """Critério estrito: a sequência é sublista contígua da cifra e todos os
    acordes da música pertencem ao conjunto da sequência.

    ``acordes_musica``/``conjunto_seq`` são opcionais e existem só para evitar
    recalcular conjuntos no laço de busca.
    """
    if not seq or len(seq) > len(cifra):
        return False

    if conjunto_seq is None:
        conjunto_seq = set(seq)
    if acordes_musica is None:
        acordes_musica = cifra

    for acorde in acordes_musica:
        if acorde not in conjunto_seq:
            return False

    tamanho = len(seq)
    for i in range(len(cifra) - tamanho + 1):
        if cifra[i:i + tamanho] == seq:
            return True
    return False

def get_similares_por_sequencia(acordes_seq, generos_key):
    # filtra para melhor desempenho
    collection = apply_filtro(musicas.values(), generos_key)
    conjunto_seq = set(acordes_seq)

    similares = []
    for musica in collection:
        if sequencia_contigua(musica.cifra, acordes_seq, musica.acordes,
                              conjunto_seq):
            similar = {
                'id_unico_musica' : musica.id_unico_musica,
                'id_artista' : musica.id_artista,
                'id_musica' : musica.id_musica,
                'nome_artista' : musica.nome_artista,
                'nome_musica' : musica.nome_musica,
                'popularidade' : musica.popularidade,
                'acordes' : musica.acordes,
                'genero' : musica.genero,
                'url' : musica.url,
            }
            similares.append(similar)

    return similares

def validar_sequencia(payload):
    """Valida o corpo do POST /sequencias e devolve (nome, acordes)."""
    if not isinstance(payload, dict):
        raise ValueError('Envie um objeto JSON com nome e acordes.')

    nome = payload.get('nome')
    if not isinstance(nome, str):
        raise ValueError('O nome deve ser um texto.')
    nome = nome.strip()
    if not nome:
        raise ValueError('O nome não pode ser vazio.')
    if len(nome) > NOME_MAX:
        raise ValueError('O nome deve ter no máximo %d caracteres.' % NOME_MAX)

    acordes_seq = payload.get('acordes')
    if not isinstance(acordes_seq, list):
        raise ValueError('Os acordes devem ser uma lista.')
    if not 1 <= len(acordes_seq) <= ACORDES_MAX:
        raise ValueError('Informe de 1 a %d acordes.' % ACORDES_MAX)

    limpos = []
    for acorde in acordes_seq:
        if not isinstance(acorde, str):
            raise ValueError('Cada acorde deve ser um texto.')
        acorde = acorde.strip()
        if not acorde:
            raise ValueError('Nenhum acorde pode ser vazio.')
        if len(acorde) > ACORDE_MAX:
            raise ValueError('Cada acorde deve ter no máximo %d caracteres.'
                             % ACORDE_MAX)
        if any(delimitador in acorde for delimitador in DELIMITADORES):
            raise ValueError('Use um acorde por item, sem ",", ";" ou "|".')
        limpos.append(acorde)

    return nome, limpos


def get_pagina(colecao, pagina_tag):
    sl = (int(pagina_tag) - 1)*TAM_PAGINA
    return colecao[sl:sl+TAM_PAGINA]

def get_similares(acordes, generos_key, id_musica = None):

    # filtra para melhor desempenho
    collection = apply_filtro(musicas.values(), generos_key)

    similares = []
    for musica in collection:

        if musica.id_unico_musica != id_musica:

            inter = set(acordes).intersection(set(musica.acordes))
            diff = set(musica.acordes) - set(acordes)

            # somente as que tiverem interseção e as que forem
            # dos generos solicitados.
            if len(inter) > 0:
                similar = {
                        'id_unico_musica' : musica.id_unico_musica,
                        'id_artista' : musica.id_artista,
                        'id_musica' : musica.id_musica,
                        'nome_artista' : musica.nome_artista,
                        'nome_musica' : musica.nome_musica,
                        'popularidade' : musica.popularidade,
                        'acordes' : musica.acordes,
                        'genero' : musica.genero,
                        'url' : musica.url,
                        'diferenca' : list(diff),
                        'intersecao' : list(inter)
                }

                similares.append(similar)

    # ordenados por menor diferença, maior interseção e maior popularidade.
    return sorted(similares, key=lambda x: (len(x['diferenca']), -len(x['intersecao'])))

## Filtra a coleção de músicas por gênero.
def apply_filtro(musicas, generos_key):
    # filtra para melhor desempenho
    collection = []
    for genero in generos_key:
        if genero in generos:
            collection += genero_musicas[genero]
    return collection

@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

if __name__ == '__main__':
    app.run(debug=True)
