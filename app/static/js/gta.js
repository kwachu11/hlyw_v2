// Dodatki w stylu GTA: banery "MISJA ZALICZONA" / "WASTED", kasa w menu, powiadomienia jak SMS-y i dźwięki.
// Użycie w grach: gta.passed('Nowy rekord', 123) albo gta.wasted('Wynik', 45).
(function () {
    var current = null, greyTimer = null;

    function esc(s) {
        return String(s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; });
    }

    function show(cls, title, label, value, ms) {
        if (current) current.remove();
        var el = document.createElement('div');
        el.className = 'gta-banner ' + cls;
        el.setAttribute('role', 'status');
        var sub = label ? esc(label) + (value != null ? ': <b>' + esc(value) + '</b>' : '') : '';
        el.innerHTML = '<div class="gta-banner-title">' + esc(title) + '</div>' + (sub ? '<div class="gta-banner-sub">' + sub + '</div>' : '');
        document.body.appendChild(el);
        current = el;
        setTimeout(function () { el.classList.add('out'); }, ms);
        setTimeout(function () { el.remove(); if (current === el) current = null; }, ms + 650);
    }

    // Kasa w menu: po grze pobieramy nowy stan i pokazujemy "+$..." (wynik zapisuje się chwilę po końcu gry)
    function fmt(n) { return '' + Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ','); }

    function refreshCash(delay) {
        var el = document.getElementById('hl-cash');
        if (!el) return;
        setTimeout(function () {
            fetch('/api/kasa', {credentials: 'same-origin'})
                .then(function (r) { return r.ok ? r.json() : null; })
                .then(function (d) {
                    if (!d) return;
                    var from = +el.dataset.cash || 0, to = d.cash;
                    if (to === from) return;
                    el.dataset.cash = to;
                    if (to > from) {
                        var plus = document.createElement('span');
                        plus.className = 'hl-cash-plus';
                        plus.textContent = '+$' + fmt(to - from);
                        el.parentNode.appendChild(plus);
                        setTimeout(function () { plus.remove(); }, 2300);
                    }
                    var t0 = performance.now();
                    (function tick(now) {
                        var k = Math.min(1, (now - t0) / 900);
                        el.textContent = fmt(from + (to - from) * k);
                        if (k < 1) requestAnimationFrame(tick);
                    })(t0);
                })
                .catch(function () {});
        }, delay);
    }

    // Powiadomienia jak SMS-y w GTA - co 45 s pytamy serwer, co nowego dodali inni
    var ICONS = {news: '📰', event: '📅', chat: '💬', photos: '📷', upgrade: '🚀'};
    var phoneBox = null;

    function phone(item) {
        if (!phoneBox) {
            phoneBox = document.createElement('div');
            phoneBox.className = 'gta-phone-stack';
            document.body.appendChild(phoneBox);
        }
        var icon = item.icon || ICONS[item.kind] || '📱';
        var a = document.createElement('a');
        a.className = 'gta-phone';
        a.href = item.url;
        var head = document.createElement('div');
        head.className = 'gta-phone-head';
        head.innerHTML = '<span>' + icon + ' Wiadomość</span><span>teraz</span>';
        var body = document.createElement('div');
        body.className = 'gta-phone-body';
        if (item.photo) {
            var img = document.createElement('img');
            img.alt = '';
            img.src = '/static/images/profile_pics/' + encodeURIComponent(item.photo);
            img.onerror = function () { img.onerror = null; img.src = '/static/images/profile_pics/default.jpg'; };
            body.appendChild(img);
        } else {
            var ic = document.createElement('span');
            ic.className = 'gta-phone-icon';
            ic.textContent = icon;
            body.appendChild(ic);
        }
        var txt = document.createElement('div');
        txt.innerHTML = '<div class="gta-phone-name">' + esc(item.username) + '</div><div class="gta-phone-text">' + esc(item.text) + '</div>';
        body.appendChild(txt);
        a.append(head, body);
        phoneBox.appendChild(a);
        while (phoneBox.children.length > 3) phoneBox.firstChild.remove();
        setTimeout(function () { a.classList.add('out'); }, 7000);
        setTimeout(function () { a.remove(); }, 7600);
        sound('sms');
    }

    function pollNotifications() {
        if (!document.getElementById('hl-cash')) return;     // tylko dla zalogowanych
        var since = null;
        try { since = sessionStorage.getItem('hl-notif-since'); } catch (e) {}
        function poll() {
            if (document.hidden) return;
            fetch('/api/powiadomienia' + (since ? '?since=' + encodeURIComponent(since) : ''), {credentials: 'same-origin'})
                .then(function (r) { return r.ok ? r.json() : null; })
                .then(function (d) {
                    if (!d) return;
                    since = d.now;
                    try { sessionStorage.setItem('hl-notif-since', since); } catch (e) {}
                    var onCamera = location.pathname.indexOf('/camera') === 0;   // czat i tak widać obok
                    d.items.filter(function (item) { return !(item.kind === 'chat' && onCamera); })
                        .forEach(function (item, i) { setTimeout(function () { phone(item); }, i * 900); });
                })
                .catch(function () {});
        }
        poll();
        setInterval(poll, 45000);
    }

    // Dźwięki generowane w przeglądarce (bez plików). Wyłącznik w stopce, zapamiętany w localStorage.
    var audio = null;
    function soundOn() { try { return localStorage.getItem('hl-sound') !== 'off'; } catch (e) { return true; } }
    function tone(ctx, freq, start, dur, type, vol) {
        var o = ctx.createOscillator(), g = ctx.createGain(), t = ctx.currentTime + start;
        o.type = type;
        o.frequency.setValueAtTime(freq, t);
        g.gain.setValueAtTime(0.0001, t);
        g.gain.exponentialRampToValueAtTime(vol, t + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
        o.connect(g); g.connect(ctx.destination);
        o.start(t); o.stop(t + dur + 0.05);
        return o;
    }
    function sound(kind) {
        if (!soundOn()) return;
        try {
            audio = audio || new (window.AudioContext || window.webkitAudioContext)();
            if (audio.state === 'suspended') audio.resume();
            if (kind === 'passed') {          // krótka fanfara w górę
                [[392, 0], [523, .12], [659, .24], [784, .36]].forEach(function (n) { tone(audio, n[0], n[1], .22, 'square', .05); });
                tone(audio, 1047, .5, .7, 'triangle', .07);
                tone(audio, 523, .5, .7, 'triangle', .05);
            } else if (kind === 'wasted') {   // niskie, opadające "bum"
                var o = tone(audio, 160, 0, 1.4, 'sawtooth', .06);
                o.frequency.exponentialRampToValueAtTime(40, audio.currentTime + 1.3);
                tone(audio, 55, 0, 1.2, 'sine', .12);
            } else if (kind === 'sms') {      // dwa krótkie piknięcia
                tone(audio, 1318, 0, .09, 'sine', .05);
                tone(audio, 1760, .12, .12, 'sine', .05);
            }
        } catch (e) {}
    }

    function setupSoundToggle() {
        var btn = document.getElementById('hl-sound-toggle');
        if (!btn) return;
        function label() { btn.textContent = soundOn() ? '🔊 Dźwięki: wł.' : '🔇 Dźwięki: wył.'; }
        label();
        btn.addEventListener('click', function () {
            try { localStorage.setItem('hl-sound', soundOn() ? 'off' : 'on'); } catch (e) {}
            label();
            sound('sms');
        });
    }

    function init() { pollNotifications(); setupSoundToggle(); }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();

    window.gta = {
        sound: sound,
        refreshCash: refreshCash,
        passed: function (label, value) {
            show('passed', 'misja zaliczona!', label || 'Nowy rekord', value, 3200);
            sound('passed');
            refreshCash(1500);
        },
        wasted: function (label, value) {
            var main = document.querySelector('.hl-main');
            if (main) {
                main.classList.add('gta-grey');
                clearTimeout(greyTimer);
                greyTimer = setTimeout(function () { main.classList.remove('gta-grey'); }, 1700);
            }
            show('wasted', 'wasted', label, value, 1700);
            sound('wasted');
            refreshCash(1500);
        },
        // Koniec gry: rozbicie to zawsze WASTED, a "misja zaliczona" pojawia się dopiero po nim i tylko przy rekordzie
        gameOver: function (score, isRecord, label) {
            window.gta.wasted(label || 'Wynik', score);
            if (isRecord) setTimeout(function () { window.gta.passed('Nowy rekord', score); }, 1900);
        }
    };
})();
