# coding: utf-8
"""Reproduz a carga de `main.py` e compara algoritmos de matching em tempo real
contra a tag pre-computada `SEQ_FAMOSA` do CSV.

Uso, a partir da raiz do repositório:

    python3 docs/features/sequencias-customizadas/generated/validate_matching.py

Não importa Flask nem `main.py`; replica o parsing de `main.py:49-98` para poder
rodar sem as dependências da aplicação instaladas.
"""
import sys

CSV = 'data/top/dataset_final.csv'

# main.py:26-34
ARTISTA_ID, MUSICA_ID, ARTISTA, MUSICA, GENERO, POPULARIDADE, TOM, SEQ_FAMOSA, CIFRA = range(9)

# main.py:40-45
SEQS = {
    0: ['Bm', 'G', 'D', 'A'],
    1: ['C', 'G', 'Am', 'F'],
    2: ['Em', 'G'],
    3: ['C', 'A7', 'Dm', 'G7'],
    4: ['Gm', 'F'],
    5: ['C', 'C7', 'F', 'Fm'],
}


def limpa_cifra(raw_cifra):
    """Cópia de main.py:11-23."""
    cifra = []
    for m in raw_cifra:
        if m.strip() != '':
            if '|' in m:
                cifra.append(m.split('|')[0].split()[0])
            else:
                cifra += [token for token in m.split()]
    return cifra


def load_rows(path=CSV):
    """Replica main.py:49-98 e devolve apenas o necessário para o matching."""
    rows = []
    with open(path) as f:
        f.readline()  # main.py:50 descarta a primeira linha
        for line in f:
            line = line.replace('"', '').replace('NA', '')[:-1]  # main.py:53
            musica = line.split(',')
            musica[POPULARIDADE] = int(musica[POPULARIDADE].replace('.', ''))
            cifra = limpa_cifra(musica[CIFRA].split(';')) if musica[CIFRA] != '' else []
            rows.append({
                'id': '%s_%s' % (musica[ARTISTA_ID], musica[MUSICA_ID]),
                'genero': musica[GENERO],
                'cifra': cifra,
                'seqs': musica[SEQ_FAMOSA].split(';'),
            })
    return rows


def contiguous(cifra, seq):
    """S aparece como sublista contígua de C (ordem importa; repetições contam)."""
    n = len(seq)
    return any(cifra[i:i + n] == seq for i in range(len(cifra) - n + 1))


def ordered_subsequence(cifra, seq):
    """S aparece em ordem em C, não necessariamente contíguo."""
    it = iter(cifra)
    return all(any(x == y for y in it) for x in seq)


def all_present(cifra, seq):
    """Todos os acordes de S aparecem em C, em qualquer ordem."""
    return set(seq) <= set(cifra)


def legacy_subset_contiguous(cifra, seq):
    """Critério de scripts/generate_data_set.py:7-24.

    S contíguo em C E todo acorde da música pertence ao conjunto de S.
    """
    return set(cifra) <= set(seq) and contiguous(cifra, seq)


def matches(rows, algo, seq):
    return {r['id'] for r in rows if algo(r['cifra'], seq)}


def main():
    rows = load_rows()
    baseline = {i: {r['id'] for r in rows if str(i) in r['seqs']} for i in SEQS}

    print('registros carregados: %d' % len(rows))
    print('registros com cifra não vazia: %d' % sum(1 for r in rows if r['cifra']))
    print()
    print('BASELINE (tag seqs_famosas):')
    for i, seq in SEQS.items():
        print('  seq %d %-12s %5d' % (i, '-'.join(seq), len(baseline[i])))
    print()

    algos = [
        ('legacy_subset_contiguous', legacy_subset_contiguous),
        ('contiguous', contiguous),
        ('ordered_subsequence', ordered_subsequence),
        ('all_present (set)', all_present),
    ]

    for name, algo in algos:
        print('=' * 78)
        print('ALGORITMO:', name)
        for i, seq in SEQS.items():
            got = matches(rows, algo, seq)
            b = baseline[i]
            print('  seq %d %-12s cand=%5d baseline=%5d equal=%-5s missing=%4d extra=%5d'
                  % (i, '-'.join(seq), len(got), len(b), got == b,
                     len(b - got), len(got - b)))
        print()

    print('=' * 78)
    print('EXEMPLOS DE SEQUÊNCIAS NOVAS (contiguous vs legacy):')
    for seq in (['C', 'G'], ['C', 'G', 'Am'], ['Am', 'F', 'C', 'G']):
        print('  %-16s contiguous=%5d legacy=%5d'
              % ('-'.join(seq),
                 len(matches(rows, contiguous, seq)),
                 len(matches(rows, legacy_subset_contiguous, seq))))


if __name__ == '__main__':
    sys.exit(main())
