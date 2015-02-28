'use strict';

angular.module('myApp.series', ['ngRoute'])

    .config(['$routeProvider', function($routeProvider) {
      $routeProvider.when('/series', {
        templateUrl: 'series/series.html',
        controller: 'SeriesCtrl'
      });
    }])

    .controller('SeriesCtrl', ['$scope', '$http', function($scope, $http) {

      $scope.episodes = {}
      $scope.episodesById = {}

      $http.get('http://localhost:8080/series').success(function(data) {
        $scope.series = data.series;
        _.each($scope.series, function(elem) {
          elem.seasons = _.range(1, elem.num_seasons + 1);
        });
      });

      $scope.onSeasonClick = function(seriesId, seasonNum) {
        // When a season is clicked, download the episodes, if they aren't already downloaded
        if (!$scope.episodes[seriesId] || !$scope.episodes[seriesId][seasonNum] || $scope.episodes[seriesId][seasonNum].length === 0) {
          $http.get('http://localhost:8080/series/' + seriesId + '/' + seasonNum + '/episodes').success(function(data) {

            var currentTime = new Date();

            if (!$scope.episodes[seriesId]) {
              $scope.episodes[seriesId] = {};
              $scope.episodesById[seriesId] = {};
            }

            // store the episodes in a sorted array, and set the seen/available flags
            var episodes = [];
            var episodeMap = {};
            _.each(data.episodes, function(val) {
              val.seen = _.contains(data.seen, val.episode);
              val.available = currentTime > new Date(val.airdate);
              episodes.push(val);
              episodeMap[val.episode] = val;
            });

            $scope.episodes[seriesId][seasonNum] = _.sortBy(episodes, function(x) { return x.episode; });
            $scope.episodesById[seriesId][seasonNum] = episodeMap;
          });
        }
      };

      $scope.onEpisodeClick = function(seriesId, seasonNum, episodeNum) {

        // If the episode isn't available, bail
        var episode = $scope.episodesById[seriesId][seasonNum][episodeNum];
        if (!episode || !episode.available)
          return;

        var request = $http({
          method: "POST",
          url: "http://localhost:8080/series",
          headers: {'Content-Type': 'application/json'},
          data: {
            seriesId: seriesId,
            season: seasonNum,
            episode: episodeNum
          }
        });

        request.success(function(data) {
            episode.seen = !episode.seen;
          });
      }
    }]);
