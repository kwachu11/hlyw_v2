// Podgląd modelu 3D (STL / 3MF / OBJ) na three.js + wymiary i orientacyjna waga oraz czas druku.
// Wymaga mapy importów z _model_viewer.html. Plik jest czytany w przeglądarce, serwer niczego nie liczy.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
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

function formatTime(seconds) {
    const minutes = Math.max(1, Math.round(seconds / 60));
    return minutes < 60 ? minutes + ' min' : Math.floor(minutes / 60) + ' h ' + (minutes % 60) + ' min';
}

export function mountViewer(box) {
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
            stats = measure(root);
            if (!stats.triangles) throw new Error('Pusty model');
            root.traverse(o => {
                if (!o.isMesh) return;
                o.geometry.computeVertexNormals();   // wiele STL-i ma w pliku zerowe normalne = czarny model
                o.material = material;
            });
            // modele do druku mają oś Z do góry, three.js - Y
            pivot = new THREE.Group();
            pivot.rotation.x = -Math.PI / 2;
            pivot.add(root);
            scene.add(pivot);
            const bounds = new THREE.Box3().setFromObject(pivot);
            pivot.position.sub(bounds.getCenter(new THREE.Vector3()));
            const size = bounds.getSize(new THREE.Vector3());
            const radius = size.length() / 2 || 1;

            const gridSize = Math.ceil(Math.max(size.x, size.z) * 1.6 / 10) * 10 || 10;
            grid = new THREE.GridHelper(gridSize, 10, 0x666666, 0x3a3a3a);
            grid.position.y = -size.y / 2;
            scene.add(grid);

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
    };
}
