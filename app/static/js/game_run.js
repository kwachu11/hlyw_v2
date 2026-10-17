// Bilet partii dla zapisu wyniku (ochrona rankingów - patrz GAME_SCORE_LIMITS w app/__init__.py).
// Gra woła hlRun.start('dino') przy starcie partii, a wynik wysyła przez hlRun.send(SAVE_URL, wynik).
(function () {
    var run = null, pending = Promise.resolve(null);

    function take() {
        // bilet jest jednorazowy - oddajemy go i zapominamy, następna partia weźmie nowy
        var p = pending;
        pending = Promise.resolve(null);
        run = null;
        return p;
    }

    window.hlRun = {
        start: function (game) {
            run = null;
            pending = fetch('/game_run/' + game, {method: 'POST', credentials: 'same-origin'})
                .then(function (r) { return r.ok ? r.json() : null; })
                .then(function (d) { run = d && d.ok ? d.run : null; return run; })
                .catch(function () { return null; });
            return pending;
        },
        // jak fetch(): zwraca obietnicę odpowiedzi; przy bardzo krótkiej partii czeka, aż bilet dojdzie
        send: function (url, score) {
            return take().then(function (id) {
                return fetch(url, {method: 'POST', credentials: 'same-origin',
                                   headers: {'Content-Type': 'application/json'},
                                   body: JSON.stringify({score: score, run: id})});
            });
        },
        // dla navigator.sendBeacon przy zamykaniu strony (bez czekania)
        body: function (score) {
            var id = run;
            take();
            return JSON.stringify({score: score, run: id});
        }
    };
})();
