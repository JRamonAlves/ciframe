angular.module('deciframeApp').controller('SequenciaController', function($http, $window, ngProgressFactory, $anchorScroll, $location, GENEROS) {
  var COR_ACORDE = '#2E1C74';

  var mapearSequencia = function(sequencia) {
    return {
      'id': sequencia.id,
      'nome': sequencia.nome,
      'acordes': sequencia.acordes.map(function(acorde) {
        return { 'acorde': acorde, 'cor': COR_ACORDE };
      })
    };
  };

  var vm = this;
  vm.sequencias = [];
  vm.novaSequencia = { 'nome': '', 'acordes': '' };
  vm.erroCadastro = '';
  vm.erroCatalogo = '';
  vm.carregandoSequencias = false;
  vm.cadastrando = false;
  vm.minhaSequencia = {};
  vm.isSearching = false;
  vm.showSearchResultsCount = false;
  vm.esfigeSpeech =  "";
  vm.musics = [];
  vm.generos = GENEROS;
  vm.meuGenero = "";
  vm.progressbar = ngProgressFactory.createInstance();

  vm.carregarSequencias = function() {
    vm.carregandoSequencias = true;
    vm.erroCatalogo = '';
    return $http.get('sequencias')
      .success(function(data) {
        vm.carregandoSequencias = false;
        vm.sequencias = data.map(mapearSequencia);
      })
      .error(function() {
        vm.carregandoSequencias = false;
        vm.erroCatalogo = "Não foi possível carregar o catálogo de sequências.";
      });
  };

  vm.carregarSequencias();

  vm.temAcorde = function(acorde) {
    if (vm.minhaSequencia.acordes) {
      return (vm.minhaSequencia.acordes.indexOf(acorde) > -1);
    } else {
      return false;
    }
  }

  vm.pesquisarPorSequencia = function(sequencia) {
    if (sequencia) {
      vm.minhaSequencia = sequencia;
    }
    if (!vm.minhaSequencia.id) {
      return;
    }
    vm.progressbar.start();
    vm.esfigeSpeech = "Procurando músicas com base na sequencia...";
    vm.isSearching = true;
    vm.showSearchResultsCount = false;
    vm.musics = [];

    var apiUrl = "";
    var searchString = "similares?sequencia_id=".concat(vm.minhaSequencia.id);
    if (vm.meuGenero !== "" && vm.meuGenero !== null) {
      searchString += "&generos="+vm.meuGenero;
    }
    $http.get(apiUrl.concat(searchString))
      .success(function(data) {
        vm.progressbar.complete();
        vm.esfigeSpeech = "Encontrei essas músicas";
        vm.isSearching = false;
        vm.showSearchResultsCount = true;
        vm.musics = data;
      })
      .error(function(data) {
        vm.progressbar.complete();
        vm.esfigeSpeech = "Ops! Algo errado.";
        vm.isSearching = false;
        vm.showSearchResultsCount = false;
      });
  }

  vm.cadastrarSequencia = function() {
    vm.erroCadastro = '';
    vm.cadastrando = true;

    var acordes = [];
    if (vm.novaSequencia.acordes) {
      acordes = vm.novaSequencia.acordes.split(',').map(function(acorde) {
        return acorde.trim();
      }).filter(function(acorde) {
        return acorde.length > 0;
      });
    }

    $http.post('sequencias', {
      'nome': vm.novaSequencia.nome,
      'acordes': acordes
    }).success(function() {
      vm.cadastrando = false;
      vm.novaSequencia = { 'nome': '', 'acordes': '' };
      vm.carregarSequencias();
    }).error(function(data, status) {
      vm.cadastrando = false;
      if (data && data.erro) {
        vm.erroCadastro = data.erro;
      } else if (status === 413) {
        vm.erroCadastro = "O cadastro é grande demais.";
      } else if (status === 400) {
        vm.erroCadastro = "Dados inválidos.";
      } else {
        vm.erroCadastro = "Não foi possível cadastrar a sequência.";
      }
    });
  }

  vm.limparPesquisa = function() {
    vm.minhaSequencia = {};
    vm.musics = [];
  }

  vm.goToLirics = function(music) {
    $window.open(music.url);
  };

  vm.goToResults = function() {
    vm.showSearchResultsCount = false;
    $("body").animate({scrollTop: $("#results").offset().top}, "slow");
  };
});
