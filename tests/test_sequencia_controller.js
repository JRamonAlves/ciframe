// Teste de regressão do controller de sequências, sem navegador.
// Roda com: node tests/test_sequencia_controller.js
const assert = require('assert');
const path = require('path');

let factory;
global.angular = {
  module: function() {
    return {
      controller: function(nome, fn) { factory = fn; }
    };
  }
};

require(path.join(__dirname, '..', 'static', 'assets', 'js', 'controllers',
  'sequencia.js'));

const chamadas = [];
let proximaGet = [];

function resposta(data) {
  const promessa = {
    success: function(cb) { cb(data); return promessa; },
    error: function() { return promessa; }
  };
  return promessa;
}

const http = {
  get: function(url) {
    chamadas.push(['GET', url]);
    return resposta(proximaGet);
  },
  post: function(url, corpo) {
    chamadas.push(['POST', url, corpo]);
    return resposta({});
  }
};

const progresso = { start: function() {}, complete: function() {} };
const vm = {};
factory.call(vm, http, { open: function() {} },
  { createInstance: function() { return progresso; } },
  function() {}, {}, ['Rock', 'Samba']);

// Carrega um catálogo em que o primeiro item tem id 0 (falsy em JS).
proximaGet = [
  { id: 0, nome: 'Sequência de Bm', acordes: ['Bm', 'G', 'D', 'A'] },
  { id: 1, nome: 'Sequência de C', acordes: ['C', 'G', 'Am', 'F'] }
];
vm.carregarSequencias();
assert.strictEqual(vm.sequencias[0].id, 0);
assert.deepStrictEqual(vm.sequencias[0].acordes, [
  { acorde: 'Bm', cor: '#2E1C74' },
  { acorde: 'G', cor: '#2E1C74' },
  { acorde: 'D', cor: '#2E1C74' },
  { acorde: 'A', cor: '#2E1C74' }
]);

// Regressão: clicar no primeiro item do catálogo (id 0) precisa buscar.
vm.pesquisarPorSequencia(vm.sequencias[0]);
assert.strictEqual(vm.minhaSequencia.id, 0);
assert.deepStrictEqual(chamadas[chamadas.length - 1],
  ['GET', 'similares?sequencia_id=0']);

// Com gênero e sem argumento, continua usando o id 0 selecionado.
vm.meuGenero = 'Rock';
vm.pesquisarPorSequencia();
assert.deepStrictEqual(chamadas[chamadas.length - 1],
  ['GET', 'similares?sequencia_id=0&generos=Rock']);

// Sem sequência selecionada, não dispara busca.
vm.limparPesquisa();
const antes = chamadas.length;
vm.pesquisarPorSequencia();
assert.strictEqual(chamadas.length, antes);

console.log('test_sequencia_controller.js: OK');
