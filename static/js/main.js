// ── NexusBank Global JS ──────────────────────────────────────

// Flash auto-dismiss
setTimeout(() => {
  document.querySelectorAll('.flash-msg').forEach(el => el.remove());
}, 5000);

// API helper
async function nbFetch(url, options = {}) {
  const defaults = {
    headers: { 'Content-Type': 'application/json' },
    ...options
  };
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    defaults.body = JSON.stringify(options.body);
  }
  if (options.body instanceof FormData) {
    delete defaults.headers['Content-Type'];
    defaults.body = options.body;
  }
  const res = await fetch(url, defaults);
  return res.json();
}

// Toast notification
function showToast(message, type = 'success') {
  const container = document.querySelector('.flash-container') || (() => {
    const c = document.createElement('div');
    c.className = 'flash-container';
    document.body.appendChild(c);
    return c;
  })();
  const icons = { success: 'check-circle', error: 'x-circle', warning: 'exclamation-triangle', info: 'info-circle' };
  const div = document.createElement('div');
  div.className = `flash-msg flash-${type}`;
  div.innerHTML = `<i class="bi bi-${icons[type] || 'info-circle'}"></i>${message}<button class="flash-close" onclick="this.parentElement.remove()"><i class="bi bi-x"></i></button>`;
  container.appendChild(div);
  setTimeout(() => div.remove(), 5000);
}

// Confirm dialog
function nbConfirm(message) {
  return new Promise(resolve => {
    const overlay = document.createElement('div');
    overlay.className = 'nb-modal-overlay open';
    overlay.innerHTML = `
      <div class="nb-modal" style="max-width:400px">
        <div style="text-align:center;padding:10px 0">
          <div style="font-size:48px;margin-bottom:16px">⚠️</div>
          <h3 style="font-size:18px;color:var(--nb-navy);margin-bottom:12px">Confirm Action</h3>
          <p style="color:var(--nb-text-2);font-size:14px;margin-bottom:28px">${message}</p>
          <div style="display:flex;gap:12px;justify-content:center">
            <button id="cnf-cancel" class="btn-secondary">Cancel</button>
            <button id="cnf-ok" class="btn-danger"><i class="bi bi-check"></i> Confirm</button>
          </div>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    document.getElementById('cnf-cancel').onclick = () => { overlay.remove(); resolve(false); };
    document.getElementById('cnf-ok').onclick = () => { overlay.remove(); resolve(true); };
  });
}

// Loading button helper
function setLoading(btn, loading) {
  if (loading) {
    btn._originalHTML = btn.innerHTML;
    btn.innerHTML = '<span class="nb-spinner"></span> Loading...';
    btn.disabled = true;
  } else {
    btn.innerHTML = btn._originalHTML || btn.innerHTML;
    btn.disabled = false;
  }
}
