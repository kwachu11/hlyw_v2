// Zmniejszanie zdjęć w przeglądarce przed wysłaniem (zgłoszenie #6 - "413 Request Entity Too Large").
// nginx przyjmuje domyślnie maks. 1 MB na zapytanie, więc duże zdjęcia skalujemy do MAX_SIDE px
// i zapisujemy jako JPEG, obniżając jakość, aż plik zmieści się w TARGET_BYTES.
// Filmy, GIF-y i pliki, których przeglądarka nie umie odczytać (np. HEIC poza Safari), zostają bez zmian.
(function () {
    var MAX_SIDE = 1920, TARGET_BYTES = 900 * 1024;

    function loadImage(file) {
        return new Promise(function (resolve, reject) {
            var url = URL.createObjectURL(file), img = new Image();
            img.onload = function () { URL.revokeObjectURL(url); resolve(img); };
            img.onerror = function () { URL.revokeObjectURL(url); reject(new Error('nie da się odczytać')); };
            img.src = url;
        });
    }

    function toBlob(canvas, quality) {
        return new Promise(function (resolve) { canvas.toBlob(resolve, 'image/jpeg', quality); });
    }

    async function shrink(file) {
        if (!/^image\/(jpeg|png|webp|bmp|heic|heif)$/i.test(file.type) || file.size <= TARGET_BYTES) return file;
        var img = await loadImage(file);
        var side = MAX_SIDE;
        for (var attempt = 0; attempt < 6; attempt++) {
            var scale = Math.min(1, side / Math.max(img.naturalWidth, img.naturalHeight));
            var canvas = document.createElement('canvas');
            canvas.width = Math.round(img.naturalWidth * scale);
            canvas.height = Math.round(img.naturalHeight * scale);
            var ctx = canvas.getContext('2d');
            ctx.fillStyle = '#fff';                  // przezroczystość z PNG -> białe tło zamiast czarnego
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            for (var q = 0.85; q >= 0.55; q -= 0.1) {
                var blob = await toBlob(canvas, q);
                if (blob && blob.size <= TARGET_BYTES) {
                    return new File([blob], file.name.replace(/\.[^.]+$/, '') + '.jpg', {type: 'image/jpeg', lastModified: Date.now()});
                }
            }
            side = Math.round(side * 0.75);
        }
        return file;
    }

    document.addEventListener('change', async function (e) {
        var input = e.target;
        if (input.tagName !== 'INPUT' || input.type !== 'file' || !input.files.length || input.dataset.hlResized) return;
        if (typeof DataTransfer === 'undefined') return;
        var form = input.form, buttons = form ? form.querySelectorAll('[type=submit]') : [];
        var info = document.createElement('small');
        info.className = 'form-text text-muted';
        info.textContent = 'Zmniejszam zdjęcie…';
        input.insertAdjacentElement('afterend', info);
        buttons.forEach(function (b) { b.disabled = true; });
        try {
            var dt = new DataTransfer(), before = 0, after = 0, changed = false;
            for (var i = 0; i < input.files.length; i++) {
                var original = input.files[i], file = original;
                try { file = await shrink(original); } catch (err) { file = original; }
                before += original.size; after += file.size; changed = changed || file !== original;
                dt.items.add(file);
            }
            if (changed) {
                input.dataset.hlResized = '1';          // przypisanie files nie wywołuje change, ale na wszelki wypadek
                input.files = dt.files;
                delete input.dataset.hlResized;
                info.textContent = 'Zdjęcie zmniejszone: ' + (before / 1048576).toFixed(1) + ' MB → ' + (after / 1048576).toFixed(1) + ' MB';
            } else {
                info.remove();
            }
            if (after > 1024 * 1024) {
                info.textContent = 'Uwaga: plik ma ' + (after / 1048576).toFixed(1) + ' MB - serwer może go nie przyjąć (limit ok. 1 MB).';
                if (!info.isConnected) input.insertAdjacentElement('afterend', info);
            }
        } finally {
            buttons.forEach(function (b) { b.disabled = false; });
        }
    });
})();
