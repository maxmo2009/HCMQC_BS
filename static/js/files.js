// File System — admin NIfTI browser + up to 6 independent 3D segmentation viewers.
// Mirrors the main app's 3D rendering (InstancedMesh per label, OrbitControls).

const MAX_PANES = 6;
const LABEL_INFO = {
    1: { name: 'LV', hex: 0xff0000, css: '#ff0000' },
    2: { name: 'RV', hex: 0x00ff00, css: '#00ff00' },
    3: { name: 'Myo', hex: 0x0088ff, css: '#0088ff' }
};

const grid = document.getElementById('fs-grid');
const emptyMsg = document.getElementById('fs-empty');
const openByPath = new Map();   // rel path -> pane element (prevent duplicates)

// HTML-escape user-controlled strings (filenames/paths from os.listdir) before
// interpolating into innerHTML. Without this, a file named e.g.
// `<img src=x onerror=alert(1)>.nii.gz` injects HTML/JS into the admin session.
function esc(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

// ---------------------------------------------------------------- 3D viewer
class SegViewer {
    constructor(container) {
        this.container = container;
        this.meshes = {};
        this.running = true;

        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0a0a);

        const w = container.clientWidth || 300;
        const h = container.clientHeight || 300;
        this.camera = new THREE.PerspectiveCamera(75, w / h, 0.1, 5000);
        this.camera.position.set(300, 300, 300);

        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(w, h);
        container.appendChild(this.renderer.domElement);

        this.scene.add(new THREE.AmbientLight(0xffffff, 0.4));
        const key = new THREE.DirectionalLight(0xffffff, 0.5); key.position.set(200, 300, 200); this.scene.add(key);
        const fill = new THREE.DirectionalLight(0xffffff, 0.3); fill.position.set(-200, 100, -100); this.scene.add(fill);
        const back = new THREE.DirectionalLight(0xffffff, 0.25); back.position.set(0, 100, -300); this.scene.add(back);
        const bottom = new THREE.DirectionalLight(0xffffff, 0.15); bottom.position.set(0, -200, 100); this.scene.add(bottom);
        this.scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 0.2));

        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = false;
        this.controls.maxPolarAngle = Math.PI;

        this._tick = this._tick.bind(this);
        this._tick();

        this._ro = new ResizeObserver(() => this.resize());
        this._ro.observe(container);
    }

    load(data) {
        this._clearMeshes();
        const [nx, ny, nz] = data.shape;
        const [sx, sy, sz] = data.spacing;
        const cx = nx / 2, cy = ny / 2, cz = nz / 2;
        const geo = new THREE.BoxGeometry(sx, sy, sz);

        const groups = {};
        data.labels.forEach((lab, i) => { (groups[lab] = groups[lab] || []).push(data.coords[i]); });

        Object.keys(groups).forEach(labStr => {
            const lab = parseInt(labStr);
            const coords = groups[labStr];
            const color = (LABEL_INFO[lab] && LABEL_INFO[lab].hex) || 0xffffff;
            const mat = new THREE.MeshPhongMaterial({
                color: color, shininess: 30, specular: 0x333333,
                emissive: color, emissiveIntensity: 0.05
            });
            const mesh = new THREE.InstancedMesh(geo, mat, coords.length);
            const m = new THREE.Matrix4();
            for (let i = 0; i < coords.length; i++) {
                m.setPosition((coords[i][0] - cx) * sx, (coords[i][1] - cy) * sy, (coords[i][2] - cz) * sz);
                mesh.setMatrixAt(i, m);
            }
            mesh.instanceMatrix.needsUpdate = true;
            this.scene.add(mesh);
            this.meshes[lab] = mesh;
        });

        // Auto-frame: position camera relative to the physical bounding sphere.
        const ext = [nx * sx, ny * sy, nz * sz];
        const radius = 0.5 * Math.sqrt(ext[0] ** 2 + ext[1] ** 2 + ext[2] ** 2) || 100;
        const d = radius * 1.9;
        this.camera.position.set(d, d, d);
        this.camera.near = Math.max(0.1, radius / 100);
        this.camera.far = radius * 30;
        this.camera.updateProjectionMatrix();
        this.controls.minDistance = radius * 0.3;
        this.controls.maxDistance = radius * 10;
        this.controls.target.set(0, 0, 0);
        this.controls.update();
    }

    setVisible(label, visible) {
        if (this.meshes[label]) this.meshes[label].visible = visible;
    }

    resize() {
        const w = this.container.clientWidth, h = this.container.clientHeight;
        if (!w || !h) return;
        this.camera.aspect = w / h;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(w, h);
    }

    _clearMeshes() {
        Object.values(this.meshes).forEach(mesh => {
            this.scene.remove(mesh);
            mesh.geometry.dispose();
            mesh.material.dispose();
        });
        this.meshes = {};
    }

    _tick() {
        if (!this.running) return;
        requestAnimationFrame(this._tick);
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    dispose() {
        this.running = false;
        if (this._ro) this._ro.disconnect();
        // OrbitControls in r128 registers ~8 DOM listeners on the canvas
        // (pointer/wheel/touch/contextmenu). Without dispose() they keep the
        // canvas → scene graph alive across pane close/reopen cycles.
        if (this.controls && this.controls.dispose) this.controls.dispose();
        this._clearMeshes();
        this.renderer.dispose();
        if (this.renderer.domElement.parentNode) {
            this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
        }
    }
}

// ---------------------------------------------------------------- panes
function updateGrid() {
    const n = openByPath.size;
    emptyMsg.style.display = n === 0 ? 'flex' : 'none';
    grid.classList.toggle('cols-2', n >= 2 && n <= 4);
    grid.classList.toggle('cols-3', n >= 5);
}

function openFile(path, name) {
    if (openByPath.has(path)) {
        const el = openByPath.get(path);
        el.animate([{ outline: '2px solid var(--accent)' }, { outline: '2px solid transparent' }], { duration: 800 });
        return;
    }
    if (openByPath.size >= MAX_PANES) {
        alert('最多同时打开 ' + MAX_PANES + ' 个 — 先关掉一个再开。');
        return;
    }

    const pane = document.createElement('div');
    pane.className = 'pane';
    pane.innerHTML =
        `<div class="pane-head">` +
        `<span class="pane-name" title="${esc(path)}">${esc(name)}</span>` +
        `<span class="pane-meta"></span>` +
        `<span class="pane-close" title="Close">✕</span>` +
        `</div>` +
        `<div class="pane-canvas"><div class="pane-loading">loading…</div></div>`;
    grid.appendChild(pane);
    openByPath.set(path, pane);
    updateGrid();

    const canvasWrap = pane.querySelector('.pane-canvas');
    const meta = pane.querySelector('.pane-meta');

    // AbortController + post-resolve identity check guards against the
    // close-during-load leak: user clicks ✕ before the fetch resolves, then
    // the deferred .then would otherwise create a SegViewer with a runaway
    // RAF loop on a detached DOM node with no path to dispose.
    const controller = new AbortController();
    pane._abort = controller;

    pane.querySelector('.pane-close').addEventListener('click', () => closePane(path));

    fetch('/api/fs/nifti?path=' + encodeURIComponent(path), { signal: controller.signal })
        .then(r => r.json().then(j => ({ ok: r.ok, j })))
        .then(({ ok, j }) => {
            // Pane may have been closed (and disposed) before fetch resolved.
            if (openByPath.get(path) !== pane) return;
            const loadingEl = canvasWrap.querySelector('.pane-loading');
            if (loadingEl) loadingEl.remove();
            if (!ok || j.status !== 'success') {
                const err = document.createElement('div');
                err.className = 'pane-error';
                err.textContent = describeError(j);
                canvasWrap.appendChild(err);
                return;
            }
            const viewer = new SegViewer(canvasWrap);
            viewer.load(j);
            pane._viewer = viewer;
            meta.textContent = `${j.num_voxels.toLocaleString()} vox · ${j.shape.join('×')}`;
            addLegend(pane, viewer, j.labels_present);
        })
        .catch(err => {
            if (err.name === 'AbortError') return;          // closed mid-load
            if (openByPath.get(path) !== pane) return;
            const loadingEl = canvasWrap.querySelector('.pane-loading');
            if (loadingEl) loadingEl.remove();
            const errEl = document.createElement('div');
            errEl.className = 'pane-error';
            errEl.textContent = 'load failed: ' + err.message;
            canvasWrap.appendChild(errEl);
        });

    markTreeRow(path, true);
}

function closePane(path) {
    const pane = openByPath.get(path);
    if (!pane) return;
    // Cancel any in-flight fetch so the .then handler bails out cleanly.
    if (pane._abort) pane._abort.abort();
    if (pane._viewer) pane._viewer.dispose();
    pane.remove();
    openByPath.delete(path);
    markTreeRow(path, false);
    updateGrid();
}

function addLegend(pane, viewer, labels) {
    if (!labels || !labels.length) return;
    const box = document.createElement('div');
    box.className = 'pane-legend';
    box.innerHTML = '<div class="lg-title">Visibility</div>';
    labels.sort((a, b) => a - b);
    labels.forEach(lab => {
        const info = LABEL_INFO[lab] || { name: 'L' + lab, css: '#ffffff' };
        const row = document.createElement('label');
        row.className = 'lg';
        row.innerHTML =
            `<input type="checkbox" class="lg-cb" checked>` +
            `<span class="dot" style="background:${info.css}"></span>` +
            `<span class="lg-name">${info.name}</span>`;
        const cb = row.querySelector('input');
        cb.addEventListener('change', () => {
            viewer.setVisible(lab, cb.checked);
            row.classList.toggle('off', !cb.checked);
        });
        box.appendChild(row);
    });
    pane.querySelector('.pane-canvas').appendChild(box);
}

function describeError(j) {
    const e = j && j.message;
    if (e === 'not_segmentation') return `不是分割图 (${j.unique} 个不同标签,像强度图)`;
    if (e === 'not_3d') return `不是 3D 体积 (ndim=${j.ndim})`;
    if (e === 'too_large') return `体积太大 (${(j.voxels || 0).toLocaleString()} 体素,超过安全上限)`;
    if (e === 'empty') return '空 (无标签)';
    if (e === 'not_found') return '文件不存在';
    if (e === 'load_failed') return '加载失败: ' + (j.detail || '文件可能损坏');
    return '无法加载: ' + (e || 'unknown');
}

// ---------------------------------------------------------------- file tree
function fmtSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
}

function markTreeRow(path, opened) {
    document.querySelectorAll(`.tree-row.is-file[data-path="${cssEscape(path)}"]`)
        .forEach(r => r.classList.toggle('opened', opened));
}

function cssEscape(s) {
    return (window.CSS && CSS.escape) ? CSS.escape(s) : s.replace(/["\\]/g, '\\$&');
}

async function fetchList(path) {
    const r = await fetch('/api/fs/list?path=' + encodeURIComponent(path));
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
}

function makeEntryNode(entry, depth) {
    const node = document.createElement('div');
    node.className = 'tree-node';

    const row = document.createElement('div');
    row.className = 'tree-row ' + (entry.type === 'dir' ? 'is-dir' : 'is-file');
    row.style.paddingLeft = (10 + depth * 14) + 'px';
    row.dataset.path = entry.path;

    if (entry.type === 'dir') {
        row.innerHTML = `<span class="caret">▸</span><span class="ic">/</span><span class="nm">${esc(entry.name)}</span>`;
        const childWrap = document.createElement('div');
        childWrap.className = 'tree-children';
        node.appendChild(row);
        node.appendChild(childWrap);

        let loaded = false;
        row.addEventListener('click', async () => {
            const isOpen = node.classList.toggle('open');
            row.querySelector('.caret').textContent = isOpen ? '▾' : '▸';
            if (isOpen && !loaded) {
                loaded = true;
                try {
                    const data = await fetchList(entry.path);
                    if (!data.entries.length) {
                        childWrap.innerHTML = '<div class="tree-empty">— empty —</div>';
                    } else {
                        data.entries.forEach(e => childWrap.appendChild(makeEntryNode(e, depth + 1)));
                    }
                } catch (err) {
                    childWrap.innerHTML = `<div class="tree-empty">error: ${err.message}</div>`;
                }
            }
        });
    } else {
        row.innerHTML = `<span class="caret"></span><span class="ic">≣</span>`
            + `<span class="nm">${esc(entry.name)}</span><span class="sz">${esc(fmtSize(entry.size))}</span>`;
        node.appendChild(row);
        row.addEventListener('click', () => openFile(entry.path, entry.name));
    }
    return node;
}

async function initTree() {
    const rootEl = document.getElementById('tree-root');
    try {
        const data = await fetchList('');
        document.getElementById('tree-head').textContent = '/' + (data.path || '');
        data.entries.forEach(e => rootEl.appendChild(makeEntryNode(e, 0)));
    } catch (err) {
        rootEl.innerHTML = `<div class="tree-empty">无法加载文件树: ${err.message}</div>`;
    }
}

initTree();
