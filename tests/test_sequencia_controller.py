# coding: utf-8
"""Executa o teste de regressão em JavaScript do controller de sequências.

O caso crítico é o primeiro item do catálogo ter id 0: em JavaScript ``!0`` é
``true``, então qualquer guarda de truthiness descartaria a "Sequência de Bm".
O teste real está em ``test_sequencia_controller.js`` e roda no Node.
"""
import os
import shutil
import subprocess
import unittest

DIRETORIO = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(DIRETORIO, 'test_sequencia_controller.js')


class TestControllerSequencia(unittest.TestCase):

    def test_primeiro_item_do_catalogo_tem_id_zero(self):
        node = shutil.which('node')
        if node is None:
            self.skipTest('node indisponível; teste do controller JS não rodou')

        resultado = subprocess.run([node, SCRIPT], capture_output=True,
                                   text=True)
        self.assertEqual(
            resultado.returncode, 0,
            'falha no teste JS:\n%s\n%s' % (resultado.stdout,
                                            resultado.stderr))


if __name__ == '__main__':
    unittest.main()
