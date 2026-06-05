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
        content.innerHTML = `<div class="err">加载失败: ${esc(e.message)}</div>`;
    }
}

function render(users) {
    if (!users.length) {
        content.innerHTML = '<div class="empty">没有用户</div>';
        return;
    }
    content.innerHTML = '';
    users.forEach(u => {
        const isAdmin = u.username === 'admin';
        const card = document.createElement('div');
        card.className = 'user-card';

        let filesHtml;
        if (!u.files.length) {
            filesHtml = '<div class="no-files">— 该用户文件夹下没有 QC 文件 —</div>';
        } else {
            filesHtml = u.files.map(f => {
                // admin 自己的文件不提供隐藏开关(admin 始终全见)
                const cb = isAdmin
                    ? '<input type="checkbox" class="vis-cb" checked disabled>'
                    : `<input type="checkbox" class="vis-cb" ${f.visible ? 'checked' : ''}`
                      + ` data-user="${esc(u.username)}" data-file="${esc(f.name)}">`;
                const cls = f.visible ? 'file-name' : 'file-name hidden-file';
                const p = f.progress || { total: 0, ed: 0, es: 0 };
                const done = p.total && p.ed === p.total && p.es === p.total;
                const prog = p.total
                    ? `<span class="file-prog${done ? ' prog-done' : ''}">ED ${p.ed}/${p.total} · ES ${p.es}/${p.total}</span>`
                    : '<span class="file-prog">— 空 —</span>';
                return `<label class="file-row">${cb}<span class="${cls}">${esc(f.name)}</span>${prog}</label>`;
            }).join('');
        }

        const selfTag = isAdmin ? '<span class="self-tag">always full</span>' : '';
        card.innerHTML =
            `<div class="user-head${isAdmin ? ' is-admin' : ''}">${esc(u.username)}`
            + ` <span class="file-count">${u.files.length} 个文件</span> ${selfTag}</div>`
            + `<div class="file-list">${filesHtml}</div>`;
        content.appendChild(card);
    });

    content.querySelectorAll('.vis-cb:not([disabled])').forEach(cb => {
        cb.addEventListener('change', () => toggleVisibility(cb));
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
        alert('设置失败: ' + e.message);
    } finally {
        cb.disabled = false;
    }
}

loadOverview();
