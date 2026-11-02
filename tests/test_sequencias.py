# coding: utf-8
"""Testes do catálogo de sequências e da busca por sequência.

Rodar a partir da raiz do repositório:

    python3 -m unittest discover -s tests -v

O CSV é carregado uma única vez, no import de ``main`` dentro de
``setUpModule``. O banco fica em um diretório temporário via ``DECIFRAME_DB``.
"""
import json
import os
import shutil
import tempfile
import unittest

DIRETORIO = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(DIRETORIO, 'fixtures', 'sequencias_originais.json')

main = None
_tmpdir = None
_env_anterior = None


def setUpModule():
    global main, _tmpdir, _env_anterior
    _tmpdir = tempfile.mkdtemp(prefix='deciframe-testes-')
    _env_anterior = os.environ.get('DECIFRAME_DB')
    os.environ['DECIFRAME_DB'] = os.path.join(_tmpdir, 'deciframe.db')

    import main as main_module
    main = main_module
    main.app.config['TESTING'] = True


def tearDownModule():
    if _env_anterior is None:
        os.environ.pop('DECIFRAME_DB', None)
    else:
        os.environ['DECIFRAME_DB'] = _env_anterior
    shutil.rmtree(_tmpdir, ignore_errors=True)


class BaseSequencias(unittest.TestCase):

    def setUp(self):
        caminho = os.environ['DECIFRAME_DB']
        for sufixo in ('', '-wal', '-shm'):
            try:
                os.remove(caminho + sufixo)
            except FileNotFoundError:
                pass
        main.db.init_db()
        self.client = main.app.test_client()

    def json_get(self, url, **params):
        resposta = self.client.get(url, query_string=params or None)
        return resposta, json.loads(resposta.get_data(as_text=True))

    def paginas(self, **params):
        paginas = []
        pagina = 1
        while True:
            consulta = dict(params)
            consulta['pagina'] = str(pagina)
            resposta, dados = self.json_get('/similares', **consulta)
            self.assertEqual(resposta.status_code, 200,
                             resposta.get_data(as_text=True))
            paginas.append([m['id_unico_musica'] for m in dados])
            if len(dados) < main.TAM_PAGINA:
                return paginas
            pagina += 1

    def criar(self, nome, acordes):
        resposta = self.client.post('/sequencias', json={
            'nome': nome,
            'acordes': acordes,
        })
        self.assertEqual(resposta.status_code, 201,
                         resposta.get_data(as_text=True))
        return json.loads(resposta.get_data(as_text=True))

    @staticmethod
    def ids(paginas):
        return [id_musica for pagina in paginas for id_musica in pagina]

    @staticmethod
    def tamanhos(paginas):
        return [len(pagina) for pagina in paginas]


class TestCatalogo(BaseSequencias):

    def test_seis_originais_na_ordem(self):
        resposta, sequencias = self.json_get('/sequencias')
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.content_type, 'text/html; charset=utf-8')
        self.assertEqual(resposta.headers['Access-Control-Allow-Origin'], '*')

        self.assertEqual([s['id'] for s in sequencias], [0, 1, 2, 3, 4, 5])
        self.assertEqual(sequencias[0]['nome'], 'Sequência de Bm')
        self.assertEqual(sequencias[0]['acordes'], ['Bm', 'G', 'D', 'A'])
        self.assertEqual(sequencias[1]['acordes'], ['C', 'G', 'Am', 'F'])
        self.assertEqual(sequencias[2]['acordes'], ['Em', 'G'])
        self.assertEqual(sequencias[3]['acordes'], ['C', 'A7', 'Dm', 'G7'])
        self.assertEqual(sequencias[4]['acordes'], ['Gm', 'F'])
        self.assertEqual(sequencias[5]['acordes'], ['C', 'C7', 'F', 'Fm'])
        for sequencia in sequencias:
            self.assertTrue(sequencia['criado_em'])

    def test_post_201_e_aparece_na_listagem(self):
        resposta = self.client.post('/sequencias', json={
            'nome': '  Minha sequência  ',
            'acordes': [' C ', 'G', 'Am'],
        })
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(resposta.content_type, 'text/html; charset=utf-8')
        criada = json.loads(resposta.get_data(as_text=True))

        self.assertGreaterEqual(criada['id'], 6)
        self.assertEqual(criada['nome'], 'Minha sequência')
        self.assertEqual(criada['acordes'], ['C', 'G', 'Am'])
        self.assertTrue(criada['criado_em'])

        _, sequencias = self.json_get('/sequencias')
        self.assertEqual(sequencias[-1], criada)
        self.assertEqual(main.db.buscar_por_id(criada['id'])['acordes'],
                         ['C', 'G', 'Am'])

    def test_repeticao_interna_e_permitida(self):
        criada = self.criar('Com repetição', ['C', 'C', 'G'])
        self.assertEqual(criada['acordes'], ['C', 'C', 'G'])

    def test_409_para_chave_duplicada(self):
        primeira = self.criar('Primeira', ['C', 'G', 'Am'])

        resposta = self.client.post('/sequencias', json={
            'nome': 'Outra com os mesmos acordes',
            'acordes': ['C', 'G', 'Am'],
        })
        self.assertEqual(resposta.status_code, 409)
        erro = json.loads(resposta.get_data(as_text=True))
        self.assertEqual(erro['id'], primeira['id'])
        self.assertIn('erro', erro)

    def test_400_para_payload_invalido(self):
        casos = [
            ('json inválido', '{nao é json'),
            ('corpo que não é objeto', []),
            ('sem nome', {'acordes': ['C']}),
            ('nome vazio', {'nome': '   ', 'acordes': ['C']}),
            ('nome grande demais', {'nome': 'x' * 121, 'acordes': ['C']}),
            ('sem acordes', {'nome': 'x'}),
            ('acordes não é lista', {'nome': 'x', 'acordes': 'C'}),
            ('lista vazia', {'nome': 'x', 'acordes': []}),
            ('acordes demais', {'nome': 'x', 'acordes': ['C'] * 33}),
            ('acorde vazio', {'nome': 'x', 'acordes': ['C', '  ']}),
            ('acorde não é texto', {'nome': 'x', 'acordes': ['C', 7]}),
            ('acorde grande demais', {'nome': 'x', 'acordes': ['C' * 17]}),
            ('vírgula no acorde', {'nome': 'x', 'acordes': ['C,D']}),
            ('ponto e vírgula no acorde', {'nome': 'x', 'acordes': ['C;D']}),
            ('barra no acorde', {'nome': 'x', 'acordes': ['C|D']}),
        ]
        for rotulo, corpo in casos:
            with self.subTest(caso=rotulo):
                if isinstance(corpo, str):
                    resposta = self.client.post(
                        '/sequencias', data=corpo,
                        content_type='application/json')
                else:
                    resposta = self.client.post('/sequencias', json=corpo)
                self.assertEqual(resposta.status_code, 400,
                                 resposta.get_data(as_text=True))
                self.assertIn('erro',
                              json.loads(resposta.get_data(as_text=True)))

    def test_413_para_payload_acima_do_limite(self):
        corpo = json.dumps({
            'nome': 'Grande',
            'acordes': ['C'] * 5000,
        })
        self.assertGreater(len(corpo), 16 * 1024)
        resposta = self.client.post('/sequencias', data=corpo,
                                    content_type='application/json')
        self.assertEqual(resposta.status_code, 413)

    def test_endpoints_existentes_mantem_contrato(self):
        urls = (
            '/generos',
            '/acordes',
            '/search?key=californication',
            '/musica/14-bis_adoraveis-criaturas/',
        )
        for url in urls:
            with self.subTest(url=url):
                resposta = self.client.get(url)
                self.assertEqual(resposta.status_code, 200)
                self.assertEqual(resposta.content_type,
                                 'text/html; charset=utf-8')
                self.assertEqual(
                    resposta.headers['Access-Control-Allow-Origin'], '*')
                self.assertIsInstance(
                    json.loads(resposta.get_data(as_text=True)),
                    (list, dict))


class TestBuscaPorSequencia(BaseSequencias):

    def test_matching_estrito_unitario(self):
        # Ordem importa.
        self.assertTrue(main.sequencia_contigua(['C', 'G'], ['C', 'G']))
        self.assertFalse(main.sequencia_contigua(['G', 'C'], ['C', 'G']))
        # Repetição interna na sequência quebra a adjacência.
        self.assertFalse(main.sequencia_contigua(['C', 'G'], ['C', 'C', 'G']))
        # Acorde extra na música exclui o match.
        self.assertFalse(main.sequencia_contigua(['C', 'G', 'D'], ['C', 'G']))
        # Sequência vazia ou maior que a cifra não casa.
        self.assertFalse(main.sequencia_contigua(['C', 'G'], []))
        self.assertFalse(main.sequencia_contigua(['C'], ['C', 'G']))
        # Repetição na música é permitida (subsequência contígua).
        self.assertTrue(main.sequencia_contigua(['C', 'C', 'G'], ['C', 'G']))

    def test_contagens_da_semantica_estrita(self):
        esperado = [
            (['C', 'G'], 20),
            (['C', 'G', 'Am'], 28),
            (['Am', 'F', 'C', 'G'], 278),
        ]
        for acordes, total in esperado:
            with self.subTest(sequencia='-'.join(acordes)):
                criada = self.criar('Teste ' + '-'.join(acordes), acordes)
                paginas = self.paginas(sequencia_id=str(criada['id']))
                self.assertEqual(len(self.ids(paginas)), total)
                # A mesma sequência é alcançável pela forma com vírgulas.
                por_string = self.paginas(sequencia=','.join(acordes))
                self.assertEqual(self.ids(por_string), self.ids(paginas))

    def test_ordem_dos_acordes_muda_o_resultado(self):
        cg = self.criar('C G', ['C', 'G'])
        gc = self.criar('G C', ['G', 'C'])
        ids_cg = self.ids(self.paginas(sequencia_id=str(cg['id'])))
        ids_gc = self.ids(self.paginas(sequencia_id=str(gc['id'])))
        self.assertNotEqual(ids_cg, ids_gc)
        self.assertNotEqual(set(ids_cg), set(ids_gc))

    def test_paginacao_e_filtro_de_genero(self):
        paginas = self.paginas(sequencia_id='1')
        self.assertEqual(self.tamanhos(paginas), [100, 100, 96])
        self.assertEqual(len(self.ids(paginas)), 296)

        resposta, dados = self.json_get('/similares', sequencia_id='1',
                                        pagina='4')
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(dados, [])

        resposta, dados = self.json_get('/similares', sequencia_id='1',
                                        generos='Rock')
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(dados)
        self.assertTrue(all(m['genero'] == 'Rock' for m in dados))
        self.assertEqual(resposta.content_type, 'text/html; charset=utf-8')

    def test_sequencia_inexistente_retorna_404(self):
        for params in ({'sequencia_id': '9999'},
                       {'sequencia_id': 'abc'},
                       {'sequencia': 'ZZZ'},
                       {'sequencia': 'CG'}):
            with self.subTest(params=params):
                resposta = self.client.get('/similares', query_string=params)
                self.assertEqual(resposta.status_code, 404)
                corpo = json.loads(resposta.get_data(as_text=True))
                self.assertIn('erro', corpo)

    def test_concatenacao_so_resolve_as_seis_originais(self):
        self.criar('C G', ['C', 'G'])
        _, por_virgulas = self.json_get('/similares', sequencia='C,G')
        self.assertTrue(por_virgulas)

        resposta = self.client.get('/similares',
                                    query_string={'sequencia': 'CG'})
        self.assertEqual(resposta.status_code, 404)

    def test_precedencia_dos_parametros(self):
        # acordes > sequencia_id
        _, dados = self.json_get('/similares', acordes='C', sequencia_id='0')
        self.assertTrue(dados)
        self.assertIn('diferenca', dados[0])
        self.assertIn('intersecao', dados[0])

        # id_unico_musica > sequencia_id
        _, dados = self.json_get('/similares',
                                 id_unico_musica='14-bis_adoraveis-criaturas',
                                 sequencia_id='0')
        self.assertTrue(dados)
        self.assertIn('diferenca', dados[0])


class TestRegressaoSequenciasOriginais(BaseSequencias):
    def setUp(self):
        super(TestRegressaoSequenciasOriginais, self).setUp()
        with open(FIXTURE) as arquivo:
            self.fixture = json.load(arquivo)

    def test_regressao_das_seis(self):
        """Compara lista, ordem e paginação das 6 com a fixture dourada.

        Com ``generos`` o resultado é determinístico e comparado página a
        página. Sem gênero, a ordem depende da iteração de ``set(generos)``
        (não determinística entre processos, inclusive no código antigo);
        para provar que matching/ordenação/paginação continuam idênticos, o
        teste reordena ``main.generos`` para a ordem de gêneros observada na
        própria fixture e compara as páginas exatas.
        """
        for item in self.fixture['sequencias']:
            formas = {
                'concatenada': ''.join(item['acordes']),
                'com_virgulas': ','.join(item['acordes']),
                'sequencia_id': str(item['id']),
            }
            parametro = {
                'concatenada': 'sequencia',
                'com_virgulas': 'sequencia',
                'sequencia_id': 'sequencia_id',
            }
            for forma, valor in formas.items():
                esperado = item['consultas']['com_virgulas']
                for genero in ('Rock', 'Samba'):
                    with self.subTest(sequencia=item['id'], forma=forma,
                                      genero=genero):
                        obtido = self.paginas(**{parametro[forma]: valor,
                                                 'generos': genero})
                        self.assertEqual(obtido, esperado[genero])

                with self.subTest(sequencia=item['id'], forma=forma,
                                  genero='todos'):
                    ordem_original = main.generos
                    try:
                        main.generos = self._ordem_generos(
                            esperado['sem_genero'])
                        obtido = self.paginas(
                            **{parametro[forma]: valor})
                    finally:
                        main.generos = ordem_original
                    self.assertEqual(obtido, esperado['sem_genero'])

    @staticmethod
    def _ordem_generos(paginas):
        """Ordem de primeira aparição dos gêneros nas páginas da fixture."""
        vistos = []
        for pagina in paginas:
            for id_musica in pagina:
                genero = main.musicas[id_musica].genero
                if genero not in vistos:
                    vistos.append(genero)
        return vistos


if __name__ == '__main__':
    unittest.main()
