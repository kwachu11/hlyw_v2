// Podgląd modelu 3D (STL / 3MF / OBJ) na three.js + wymiary i orientacyjna waga oraz czas druku.
// Wymaga mapy importów z _model_viewer.html. Plik jest czytany w przeglądarce, serwer niczego nie liczy.
// Ustawienie do druku (obroty o 90°, odbicia, skala) to lista operacji {ops, scale} - zapisywana z propozycją,
// żeby admin mógł ustawić model tak samo w slicerze (albo pobrać gotowy STL po zmianach).
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { STLExporter } from 'three/addons/exporters/STLExporter.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';
import { ThreeMFLoader } from 'three/addons/loaders/3MFLoader.js';
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';

export const VIEWABLE = ['stl', '3mf', 'obj'];

// Szacunek bez krajania: ścianki + 15% wypełnienia, średni przepływ dla danej jakości, bez podpór.
const DENSITY = { 'PLA': 1.24, 'PETG': 1.27, 'TPU (elastyczny)': 1.21, 'ABS': 1.04, 'ASA': 1.07 };   // g/cm³
const PROFILE = {                  // wysokość warstwy (mm), średni przepływ (mm³/s)
    szkic: [0.28, 14],
    standard: [0.20, 9],
    dokladna: [0.12, 4],
};
const WALL_MM = 0.8, INFILL = 0.15, SECONDS_PER_LAYER = 2;

function parseModel(buffer, ext) {
    if (ext === 'stl') return new THREE.Mesh(new STLLoader().parse(buffer));
    if (ext === '3mf') return new ThreeMFLoader().parse(buffer);
    if (ext === 'obj') return new OBJLoader().parse(new TextDecoder().decode(buffer));
    throw new Error('Nieobsługiwany format: ' + ext);
}

// objętość (mm³) i powierzchnia (mm²) siatki - suma po trójkątach; objętość ze wzoru na czworościany
function measure(root) {
    root.updateMatrixWorld(true);
    const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3(), cross = new THREE.Vector3();
    const box = new THREE.Box3();
    let volume = 0, area = 0, triangles = 0;
    root.traverse(mesh => {
        if (!mesh.isMesh) return;
        const pos = mesh.geometry.attributes.position, index = mesh.geometry.index;
        const count = index ? index.count : pos.count;
        const at = (v, i) => v.fromBufferAttribute(pos, index ? index.getX(i) : i).applyMatrix4(mesh.matrixWorld);
        for (let i = 0; i + 2 < count; i += 3) {
            at(a, i); at(b, i + 1); at(c, i + 2);
            box.expandByPoint(a); box.expandByPoint(b); box.expandByPoint(c);
            volume += a.dot(cross.crossVectors(b, c)) / 6;
            area += cross.subVectors(b, a).cross(c.clone().sub(a)).length() / 2;
            triangles++;
        }
    });
    return { volume: Math.abs(volume), area, triangles, size: box.getSize(new THREE.Vector3()) };
}

// operacje w osiach stołu drukarki (Z do góry): obrót o +90° albo odbicie lustrzane
export const OPS = {
    rx: new THREE.Matrix4().makeRotationX(Math.PI / 2),
    ry: new THREE.Matrix4().makeRotationY(Math.PI / 2),
    rz: new THREE.Matrix4().makeRotationZ(Math.PI / 2),
    mx: new THREE.Matrix4().makeScale(-1, 1, 1),
    my: new THREE.Matrix4().makeScale(1, -1, 1),
    mz: new THREE.Matrix4().makeScale(1, 1, -1),
};
export const SCALE_MIN = 10, SCALE_MAX = 500;
// kolory osi jak w Bambu Studio / większości slicerów
export const AXIS_COLORS = { x: '#e5484d', y: '#46a758', z: '#3e8ed0' };

// podpis osi (litera na kółku) jako sprite - zawsze zwrócony do kamery
function axisLabel(text, color, size) {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 64;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(32, 32, 30, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 40px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 32, 34);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), depthTest: false }));
    sprite.scale.set(size, size, 1);
    sprite.renderOrder = 10;
    return sprite;
}

// strzałki X / Y / Z w lewym przednim rogu stołu (w three.js: X = X, Y stołu = -Z, Z stołu = Y)
function axesHelper(gridSize, floorY) {
    const group = new THREE.Group();
    const length = gridSize * 0.22, head = length * 0.22, label = gridSize * 0.06;
    const origin = new THREE.Vector3(-gridSize / 2, floorY, gridSize / 2);
    [['X', new THREE.Vector3(1, 0, 0), AXIS_COLORS.x],
     ['Y', new THREE.Vector3(0, 0, -1), AXIS_COLORS.y],
     ['Z', new THREE.Vector3(0, 1, 0), AXIS_COLORS.z]].forEach(([name, dir, color]) => {
        group.add(new THREE.ArrowHelper(dir, origin, length, color, head, head * 0.6));
        const sprite = axisLabel(name, color, label);
        sprite.position.copy(origin).addScaledVector(dir, length + label * 0.8);
        group.add(sprite);
    });
    return group;
}

function disposeTree(object) {
    object.traverse(o => {
        if (o.geometry) o.geometry.dispose();
        if (o.material) { if (o.material.map) o.material.map.dispose(); o.material.dispose(); }
    });
}

export function cleanTransform(t) {
    const ops = (t && Array.isArray(t.ops) ? t.ops : []).filter(op => op in OPS).slice(0, 60);
    const scale = Math.min(SCALE_MAX, Math.max(SCALE_MIN, Math.round(Number(t && t.scale) || 100)));
    return { ops, scale };
}

function transformMatrix(t) {
    const m = new THREE.Matrix4();
    t.ops.forEach(op => m.premultiply(OPS[op]));          // każda kolejna operacja w osiach stołu
    return m.premultiply(new THREE.Matrix4().makeScale(t.scale / 100, t.scale / 100, t.scale / 100));
}

// opis dla ludzi, np. „obrót X 90° → Z 180°, odbicie X, skala 120%” (to samo liczy serwer: describe_print_transform)
export function describeTransform(t) {
    t = cleanTransform(t);
    const parts = [], steps = [];
    t.ops.forEach(op => {
        const last = steps[steps.length - 1];
        if (last && last.op === op) last.n++; else steps.push({ op, n: 1 });
    });
    const rotations = [], mirrors = [];
    steps.forEach(({ op, n }) => {
        const axis = op[1].toUpperCase();
        if (op[0] === 'r' && n % 4) rotations.push(`${axis} ${(n % 4) * 90}°`);
        if (op[0] === 'm' && n % 2) mirrors.push(axis);
    });
    if (rotations.length) parts.push('obrót ' + rotations.join(' → '));
    if (mirrors.length) parts.push('odbicie ' + mirrors.join(', '));
    if (t.scale !== 100) parts.push(`skala ${t.scale}%`);
    return parts.join(', ');
}

function formatTime(seconds) {
    const minutes = Math.max(1, Math.round(seconds / 60));
    return minutes < 60 ? minutes + ' min' : Math.floor(minutes / 60) + ' h ' + (minutes % 60) + ' min';
}

export function mountViewer(box, { editable = false, onTransform = null } = {}) {
    const stage = box.querySelector('.hl-model-stage'), statsEl = box.querySelector('.hl-model-stats');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1b1d20);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 2));
    const sun = new THREE.DirectionalLight(0xffffff, 2);
    scene.add(sun);

    const camera = new THREE.PerspectiveCamera(40, 1, 1, 10000);
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    stage.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.addEventListener('change', render);

    const material = new THREE.MeshStandardMaterial({ color: 0xb0b0b0, roughness: 0.55, metalness: 0.05 });
    let pivot = null, grid = null, stats = null, options = {};
    let base = null, holder = null, axes = null, transform = cleanTransform();   // base = pomiary modelu przed ustawieniem
    let toolbar = null;

    function render() {
        sun.position.copy(camera.position);
        renderer.render(scene, camera);
    }
    function resize() {
        const w = stage.clientWidth, h = stage.clientHeight;
        if (!w || !h) return;
        renderer.setSize(w, h);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        render();
    }
    new ResizeObserver(resize).observe(stage);

    function clear() {
        if (pivot) {
            scene.remove(pivot);
            pivot.traverse(o => { if (o.isMesh) o.geometry.dispose(); });
            pivot = null;
        }
        if (grid) { scene.remove(grid); grid.geometry.dispose(); grid = null; }
        if (axes) { scene.remove(axes); disposeTree(axes); axes = null; }
        holder = null; base = null;
    }

    // ułożenie na stole po każdej zmianie: model na środku, siatka pod spodem
    function layout() {
        holder.matrix.copy(transformMatrix(transform));
        holder.matrixWorldNeedsUpdate = true;
        pivot.position.set(0, 0, 0);
        pivot.updateMatrixWorld(true);
        const bounds = new THREE.Box3().setFromObject(pivot, true);
        pivot.position.sub(bounds.getCenter(new THREE.Vector3()));
        const size = bounds.getSize(new THREE.Vector3());
        const k = transform.scale / 100;
        // three.js ma Y do góry: wymiary na stole X × Y × Z = świat X × Z × Y
        stats = { volume: base.volume * k ** 3, area: base.area * k ** 2, triangles: base.triangles,
                  size: new THREE.Vector3(size.x, size.z, size.y) };
        if (grid) { scene.remove(grid); grid.geometry.dispose(); }
        const gridSize = Math.ceil(Math.max(size.x, size.z) * 1.6 / 10) * 10 || 10;
        grid = new THREE.GridHelper(gridSize, 10, 0x666666, 0x3a3a3a);
        grid.position.y = -size.y / 2;
        scene.add(grid);
        if (axes) { scene.remove(axes); disposeTree(axes); }
        axes = axesHelper(gridSize, -size.y / 2);
        scene.add(axes);
        return size;
    }

    function setTransform(next, notify) {
        transform = cleanTransform(next);
        if (toolbar) toolbar.querySelector('[data-scale]').value = transform.scale;
        if (pivot) {
            const size = layout();
            // kamera z tego samego kierunku, ale z odległością dopasowaną do nowej wielkości modelu
            const radius = size.length() / 2 * 1.3 || 1;
            const direction = camera.position.clone().sub(controls.target).normalize();
            controls.target.set(0, 0, 0);
            camera.position.copy(direction.multiplyScalar(radius * 2.9));
            camera.near = radius / 100;
            camera.far = radius * 100;
            camera.updateProjectionMatrix();
            controls.update();
            showStats();
            render();
        }
        if (notify && onTransform) onTransform(transform);
    }

    // pasek ustawiania modelu (tylko w formularzu)
    if (editable) {
        toolbar = document.createElement('div');
        toolbar.className = 'hl-model-tools';
        toolbar.innerHTML =
            '<span class="hl-model-tools-label">Obróć o 90°</span>' +
            '<button type="button" data-op="rx" title="Obróć wokół osi X">⟳ <b class="hl-axis-x">X</b></button>' +
            '<button type="button" data-op="ry" title="Obróć wokół osi Y">⟳ <b class="hl-axis-y">Y</b></button>' +
            '<button type="button" data-op="rz" title="Obróć wokół osi Z (pionowej)">⟳ <b class="hl-axis-z">Z</b></button>' +
            '<span class="hl-model-tools-label">Odbij</span>' +
            '<button type="button" data-op="mx" title="Odbicie lustrzane w osi X">⇋ <b class="hl-axis-x">X</b></button>' +
            '<button type="button" data-op="my" title="Odbicie lustrzane w osi Y">⇋ <b class="hl-axis-y">Y</b></button>' +
            '<button type="button" data-op="mz" title="Odbicie lustrzane w osi Z">⇋ <b class="hl-axis-z">Z</b></button>' +
            '<label class="hl-model-tools-label mb-0">Skala <input type="number" data-scale min="' + SCALE_MIN +
            '" max="' + SCALE_MAX + '" step="5" value="100"> %</label>' +
            '<button type="button" data-reset>↺ Reset</button>';
        stage.after(toolbar);
        toolbar.querySelectorAll('[data-op]').forEach(b => b.addEventListener('click', () =>
            setTransform({ ops: transform.ops.concat(b.dataset.op), scale: transform.scale }, true)));
        toolbar.querySelector('[data-scale]').addEventListener('change', e =>
            setTransform({ ops: transform.ops, scale: e.target.value }, true));
        toolbar.querySelector('[data-reset]').addEventListener('click', () => setTransform(null, true));
    }

    function showStats() {
        if (!stats) return;
        const { volume, area, size } = stats;
        const [layer, flow] = PROFILE[options.quality] || PROFILE.standard;
        const quantity = Math.max(1, parseInt(options.quantity, 10) || 1);
        const shell = Math.min(volume, area * WALL_MM);
        const printed = shell + (volume - shell) * INFILL;              // mm³ faktycznie wydrukowane
        const grams = printed / 1000 * (DENSITY[options.material] || DENSITY.PLA) * quantity;
        const seconds = (printed / flow + size.z / layer * SECONDS_PER_LAYER) * quantity;
        const num = (value, digits) => value.toFixed(digits).replace('.', ',');
        const parts = [`${num(size.x, 1)} × ${num(size.y, 1)} × ${num(size.z, 1)} mm`,
                       `ok. ${num(grams, grams < 10 ? 1 : 0)} g filamentu`,
                       `ok. ${formatTime(seconds)} druku`];
        statsEl.textContent = parts.join(' · ') + (quantity > 1 ? ` (razem ${quantity} szt.)` : '') +
            ' - orientacyjnie, bez podpór';
    }

    return {
        load(buffer, ext) {
            clear();
            const root = parseModel(buffer, ext);
            base = measure(root);
            if (!base.triangles) throw new Error('Pusty model');
            root.traverse(o => {
                if (!o.isMesh) return;
                o.geometry.computeVertexNormals();   // wiele STL-i ma w pliku zerowe normalne = czarny model
                o.material = material;
            });
            // modele do druku mają oś Z do góry, three.js - Y
            pivot = new THREE.Group();
            pivot.rotation.x = -Math.PI / 2;
            holder = new THREE.Group();            // ustawienie do druku (macierz z listy operacji)
            holder.matrixAutoUpdate = false;
            holder.add(root);
            pivot.add(holder);
            scene.add(pivot);
            const size = layout();
            const radius = size.length() / 2 * 1.3 || 1;   // zapas, żeby po obrotach model dalej się mieścił

            camera.near = radius / 100;
            camera.far = radius * 100;
            camera.position.set(radius * 1.6, radius * 1.1, radius * 2.2);
            camera.updateProjectionMatrix();
            controls.target.set(0, 0, 0);
            controls.update();
            box.hidden = false;
            resize();
            showStats();
        },
        setOptions(next) {
            Object.assign(options, next);
            if (next.color) {
                material.color.set(next.color === 'transparent' ? 0xb0b0b0 : next.color);
                render();
            }
            showStats();
        },
        hide() { clear(); stats = null; box.hidden = true; statsEl.textContent = ''; },
        setTransform(next) { setTransform(next, false); },
        getTransform() { return cleanTransform(transform); },
        // binarny STL modelu po ustawieniu (osie stołu, Z do góry) - do pobrania przez admina
        exportStl() {
            if (!pivot) return null;
            const position = pivot.position.clone(), rotation = pivot.rotation.clone();
            pivot.position.set(0, 0, 0);
            pivot.rotation.set(0, 0, 0);
            pivot.updateMatrixWorld(true);
            const data = new STLExporter().parse(pivot, { binary: true });
            if (transformMatrix(transform).determinant() < 0) {
                // odbicie lustrzane odwraca kolejność wierzchołków - bez tego ścianki byłyby „do środka”
                const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
                for (let i = 0, n = view.getUint32(80, true); i < n; i++) {
                    const t = 84 + i * 50;
                    for (let k = 0; k < 3; k++) {
                        view.setFloat32(t + k * 4, -view.getFloat32(t + k * 4, true), true);
                        const a = view.getFloat32(t + 24 + k * 4, true);
                        view.setFloat32(t + 24 + k * 4, view.getFloat32(t + 36 + k * 4, true), true);
                        view.setFloat32(t + 36 + k * 4, a, true);
                    }
                }
            }
            pivot.position.copy(position);
            pivot.rotation.copy(rotation);
            pivot.updateMatrixWorld(true);
            return new Blob([data], { type: 'model/stl' });
        },
    };
}
