# coding: utf-8
"""Catálogo persistido de sequências de acordes.

Usa apenas a stdlib (sqlite3). O caminho do banco vem de ``DECIFRAME_DB`` ou,
quando ausente, de ``<instance_path>/deciframe.db`` (por padrão,
``instance/deciframe.db`` na raiz do projeto).

O banco guarda as seis sequências originais como linhas normais (IDs 0..5) e
todas as sequências cadastradas por visitantes. A ``chave`` é a lista de
acordes unida por vírgula, preservando a ordem.
"""
import contextlib
import datetime
import json
import os
import sqlite3

DIRETORIO_PADRAO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'instance')

SCHEMA = '''
CREATE TABLE IF NOT EXISTS sequencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    acordes_json TEXT NOT NULL,
    chave TEXT NOT NULL UNIQUE,
    criado_em TEXT NOT NULL
)
'''

# Espelha data/mapeamento_sequencias_famosas.txt e o antigo dict de main.py.
SEQUENCIAS_ORIGINAIS = (
    (0, 'Sequência de Bm', ['Bm', 'G', 'D', 'A']),
    (1, 'Sequência de C', ['C', 'G', 'Am', 'F']),
    (2, 'Sequência Em', ['Em', 'G']),
    (3, 'Sequência de C (Samba)', ['C', 'A7', 'Dm', 'G7']),
    (4, 'Sequência de Gm', ['Gm', 'F']),
    (5, 'Sequência de C (Samba cont.)', ['C', 'C7', 'F', 'Fm']),
)

# A concatenação legada (``BmGDA``) não é reversível em geral; o mapa cobre
# apenas as seis originais. Sequências novas só resolvem pela forma com
# vírgulas, que é a ``chave`` do catálogo.
LEGACY_STRINGS = {
    ''.join(acordes): id_seq for id_seq, _, acordes in SEQUENCIAS_ORIGINAIS
}


class SequenciaDuplicada(Exception):
    """Levantada quando a ``chave`` já existe no catálogo."""

    def __init__(self, id_existente):
        super(SequenciaDuplicada, self).__init__(
            'Sequência já cadastrada (id %s).' % id_existente)
        self.id_existente = id_existente


def caminho_banco(instance_path=None):
    """Resolve o caminho do banco a cada operação (facilita testes)."""
    return os.environ.get('DECIFRAME_DB') or os.path.join(
        instance_path or DIRETORIO_PADRAO, 'deciframe.db')


@contextlib.contextmanager
def conexao(instance_path=None):
    """Abre uma conexão por operação e garante commit/rollback/fechamento."""
    caminho = caminho_banco(instance_path)
    diretorio = os.path.dirname(caminho)
    if diretorio:
        os.makedirs(diretorio, exist_ok=True)

    conn = sqlite3.connect(caminho, timeout=5)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=5000')
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _agora():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _linha_para_dict(linha):
    return {
        'id': linha['id'],
        'nome': linha['nome'],
        'acordes': json.loads(linha['acordes_json']),
        'criado_em': linha['criado_em'],
    }


def init_db(instance_path=None):
    """Cria a tabela e garante as seis originais (idempotente)."""
    with conexao(instance_path) as conn:
        conn.execute(SCHEMA)
        criado_em = _agora()
        for id_seq, nome, acordes in SEQUENCIAS_ORIGINAIS:
            conn.execute(
                'INSERT OR IGNORE INTO sequencias '
                '(id, nome, acordes_json, chave, criado_em) '
                'VALUES (?, ?, ?, ?, ?)',
                (id_seq, nome, json.dumps(acordes, ensure_ascii=False),
                 ','.join(acordes), criado_em))


def listar_sequencias(instance_path=None):
    with conexao(instance_path) as conn:
        linhas = conn.execute(
            'SELECT id, nome, acordes_json, criado_em '
            'FROM sequencias ORDER BY id').fetchall()
    return [_linha_para_dict(linha) for linha in linhas]


def buscar_por_id(id_seq, instance_path=None):
    with conexao(instance_path) as conn:
        linha = conn.execute(
            'SELECT id, nome, acordes_json, criado_em '
            'FROM sequencias WHERE id = ?', (id_seq,)).fetchone()
    return _linha_para_dict(linha) if linha is not None else None


def buscar_por_chave(chave, instance_path=None):
    with conexao(instance_path) as conn:
        linha = conn.execute(
            'SELECT id, nome, acordes_json, criado_em '
            'FROM sequencias WHERE chave = ?', (chave,)).fetchone()
    return _linha_para_dict(linha) if linha is not None else None


def criar_sequencia(nome, acordes, instance_path=None):
    """Insere uma sequência e devolve o objeto criado.

    Levanta ``SequenciaDuplicada`` com o id existente quando a mesma lista,
    na mesma ordem, já está no catálogo.
    """
    acordes = list(acordes)
    chave = ','.join(acordes)
    criado_em = _agora()
    with conexao(instance_path) as conn:
        try:
            cursor = conn.execute(
                'INSERT INTO sequencias (nome, acordes_json, chave, criado_em) '
                'VALUES (?, ?, ?, ?)',
                (nome, json.dumps(acordes, ensure_ascii=False), chave,
                 criado_em))
        except sqlite3.IntegrityError:
            linha = conn.execute(
                'SELECT id FROM sequencias WHERE chave = ?',
                (chave,)).fetchone()
            if linha is None:
                raise
            raise SequenciaDuplicada(linha['id'])
    return {
        'id': cursor.lastrowid,
        'nome': nome,
        'acordes': acordes,
        'criado_em': criado_em,
    }


def resolver_sequencia_legada(seq):
    """Resolve a forma concatenada antiga (``BmGDA``) para um id."""
    if not seq:
        return None
    return LEGACY_STRINGS.get(seq.replace(',', ''))
