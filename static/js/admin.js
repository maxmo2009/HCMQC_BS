// Admin Tools — list users + their QC files, toggle per-user file visibility.
// Admin-only page (server enforces @admin_required; the menu entry is also gated).

const content = document.getElementById('admin-content');

// Escape filesystem/user-controlled strings before innerHTML.
function esc(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

async function loadOverview() {
    try {
        const r = await fetch('/api/admin/overview');
        const d = await r.json();
        if (!r.ok || d.status !== 'success') throw new Error(d.message || ('HTTP ' + r.status));
        render(d.users || []);
    } catch (e) {
        content.innerHTML = `<div class="err">Failed to load: ${esc(e.message)}</div>`;
    }
}

function render(users) {
    if (!users.length) {
        content.innerHTML = '<div class="empty">No users</div>';
        return;
    }
    content.innerHTML = '';
    users.forEach(u => {
        const isAdmin = u.username === 'admin';
        const card = document.createElement('div');
        card.className = 'user-card';

        let filesHtml;
        if (!u.files.length) {
            filesHtml = '<div class="no-files">— No QC files in this user\'s folder —</div>';
        } else {
            filesHtml = u.files.map(f => {
                // admin's own files get no hide toggle (admin always sees everything)
                const cb = isAdmin
                    ? '<input type="checkbox" class="vis-cb" checked disabled>'
                    : `<input type="checkbox" class="vis-cb" ${f.visible ? 'checked' : ''}`
                      + ` data-user="${esc(u.username)}" data-file="${esc(f.name)}">`;
                const cls = f.visible ? 'file-name' : 'file-name hidden-file';
                const p = f.progress || { total: 0, ed: 0, es: 0 };
                const done = p.total && p.ed === p.total && p.es === p.total;
                // Overall completion across both phases (ED + ES out of 2 per patient).
                const pct = p.total ? Math.round((p.ed + p.es) / (p.total * 2) * 100) : 0;
                const prog = p.total
                    ? `<span class="file-prog${done ? ' prog-done' : ''}">ED ${p.ed}/${p.total} · ES ${p.es}/${p.total}</span>`
                    : '<span class="file-prog">— empty —</span>';
                // pct is a server-derived integer — safe to inline as a width.
                const bar = p.total
                    ? `<span class="file-bar" title="${pct}% (${p.ed + p.es}/${p.total * 2})">`
                      + `<span class="file-bar-fill${done ? ' bar-done' : ''}" style="width:${pct}%"></span></span>`
                    : '';
                return `<label class="file-row">${cb}<span class="${cls}">${esc(f.name)}</span>`
                    + `<span class="file-meta">${bar}${prog}</span></label>`;
            }).join('');
        }

        const selfTag = isAdmin ? '<span class="self-tag">always full</span>' : '';
        // The admin account can't be deleted (avoid locking yourself out); any account's password can be changed.
        const delBtn = isAdmin ? ''
            : `<button class="admin-btn act-del danger" data-user="${esc(u.username)}">Delete</button>`;
        const actions =
            `<span class="head-actions">`
            + `<button class="admin-btn act-pw" data-user="${esc(u.username)}">Change Password</button>`
            + delBtn + `</span>`;
        card.innerHTML =
            `<div class="user-head${isAdmin ? ' is-admin' : ''}">${esc(u.username)}`
            + ` <span class="file-count">${u.files.length} file${u.files.length === 1 ? '' : 's'}</span> ${selfTag}${actions}</div>`
            + `<div class="file-list">${filesHtml}</div>`;
        content.appendChild(card);
    });

    content.querySelectorAll('.vis-cb:not([disabled])').forEach(cb => {
        cb.addEventListener('change', () => toggleVisibility(cb));
    });
    content.querySelectorAll('.act-pw').forEach(b => {
        b.addEventListener('click', () => changePassword(b.dataset.user));
    });
    content.querySelectorAll('.act-del').forEach(b => {
        b.addEventListener('click', () => openDeleteModal(b.dataset.user));
    });
}

async function toggleVisibility(cb) {
    const username = cb.dataset.user;
    const filename = cb.dataset.file;
    const visible = cb.checked;
    cb.disabled = true;
    try {
        const r = await fetch('/api/admin/visibility', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, filename, visible })
        });
        const d = await r.json();
        if (!r.ok || d.status !== 'success') throw new Error(d.message || ('HTTP ' + r.status));
        const nameSpan = cb.parentElement.querySelector('.file-name');
        if (nameSpan) nameSpan.classList.toggle('hidden-file', !visible);
    } catch (e) {
        cb.checked = !visible;   // revert on failure
        alert('Update failed: ' + e.message);
    } finally {
        cb.disabled = false;
    }
}

// ── Account management ──────────────────────────────────────────────────────
const acctMsg = document.getElementById('acct-msg');

function flashAcct(text, ok) {
    acctMsg.textContent = text;
    acctMsg.className = ok ? 'ok' : 'bad';
}

async function postJSON(url, body) {
    const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    let d = {};
    try { d = await r.json(); } catch (e) { /* non-JSON error */ }
    if (!r.ok || d.status !== 'success') {
        throw new Error(d.message || ('HTTP ' + r.status));
    }
    return d;
}

// Add user
document.getElementById('add-user-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const uEl = document.getElementById('new-username');
    const pEl = document.getElementById('new-password');
    const username = uEl.value.trim();
    const password = pEl.value;
    if (!username || !password) { flashAcct('Username and password are both required', false); return; }
    try {
        await postJSON('/api/admin/user', { username, password });
        uEl.value = ''; pEl.value = '';
        flashAcct(`Added account "${username}"`, true);
        loadOverview();
    } catch (err) {
        flashAcct('Add failed: ' + err.message, false);
    }
});

// Change password (prompt — username/value are plain text, no HTML injection)
async function changePassword(username) {
    const pw = prompt(`Set a new password for account "${username}":`);
    if (pw === null) return;            // cancelled
    if (!pw) { flashAcct('Password cannot be empty', false); return; }
    try {
        await postJSON('/api/admin/user/password', { username, password: pw });
        flashAcct(`Updated password for "${username}"`, true);
    } catch (err) {
        flashAcct(`Failed to change password for "${username}": ` + err.message, false);
    }
}

// Delete user (modal with optional data-folder removal)
const delModal = document.getElementById('del-modal');
const delDataCb = document.getElementById('del-data-cb');
let delTarget = null;

function openDeleteModal(username) {
    delTarget = username;
    document.getElementById('del-name').textContent = username;
    delDataCb.checked = false;
    delModal.hidden = false;
}
function closeDeleteModal() { delModal.hidden = true; delTarget = null; }

document.getElementById('del-cancel').addEventListener('click', closeDeleteModal);
delModal.addEventListener('click', (e) => { if (e.target === delModal) closeDeleteModal(); });
document.getElementById('del-confirm').addEventListener('click', async () => {
    if (!delTarget) return;
    const username = delTarget;
    const deleteData = delDataCb.checked;
    try {
        await postJSON('/api/admin/user/delete', { username, delete_data: deleteData });
        closeDeleteModal();
        flashAcct(`Deleted account "${username}"${deleteData ? ' and its data' : ' (data kept)'}`, true);
        loadOverview();
    } catch (err) {
        closeDeleteModal();
        flashAcct(`Failed to delete "${username}": ` + err.message, false);
    }
});

loadOverview();
