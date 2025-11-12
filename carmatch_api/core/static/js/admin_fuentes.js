(() => {
  const API_LIST   = "/api/n8n/flows/";
  const API_TOGGLE = (id) => `/api/n8n/flows/${id}/toggle/`;
  const API_RUNNOW = (id) => `/api/n8n/flows/${id}/run-now/`; // requiere endpoint por flujo

  const state = document.getElementById('state');
  const rows  = document.getElementById('rows');

  const setState = (html='') => state.innerHTML = html;

  // CSRF (por si proteges los POST)
  function getCookie(name) {
    const v = `; ${document.cookie}`;
    const p = v.split(`; ${name}=`);
    if (p.length === 2) return p.pop().split(';').shift();
  }
  const CSRF = getCookie('csrftoken');

  const fmtDate = (iso) => !iso ? '—' : new Date(iso).toLocaleString('es-CL');
  const badge = (enabled) => enabled
    ? '<span class="badge text-bg-success">Activo</span>'
    : '<span class="badge text-bg-secondary">Inactivo</span>';

  function row(flow) {
    const hora = flow.schedule_time || '—';
    const freq = flow.frequency    || '—';
    const runBtn = flow.has_webhook
      ? `<button class="btn btn-outline-secondary btn-sm" data-action="run">Ejecutar ahora</button>`
      : `<button class="btn btn-outline-secondary btn-sm" disabled title="Sin webhook configurado">Ejecutar ahora</button>`;

    return `
      <tr data-id="${flow.id}">
        <td class="text-muted"><i class="bi bi-diagram-3 fs-4"></i></td>
        <td>
          <div class="fw-semibold">${flow.name || '(sin nombre)'}</div>
          <div class="small text-muted">
            ${flow.n8n_url ? `<a href="${flow.n8n_url}" target="_blank" rel="noopener">Abrir en n8n</a>` : ''}
          </div>
        </td>
        <td><code>${hora}</code></td>
        <td>${freq}</td>
        <td>${fmtDate(flow.last_run)}</td>
        <td class="status">${badge(!!flow.enabled)}</td>
        <td class="text-end">
          <div class="btn-group">
            <button class="btn btn-outline-secondary btn-sm" data-action="toggle">
              ${flow.enabled ? 'Desactivar' : 'Activar'}
            </button>
            <a class="btn btn-outline-primary btn-sm" href="${flow.n8n_url || '#'}" target="_blank" rel="noopener">Editar flujo</a>
            ${runBtn}
          </div>
        </td>
      </tr>
    `;
  }

  function bindRowActions() {
    // Activar/Desactivar
    rows.querySelectorAll('button[data-action="toggle"]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const tr = e.target.closest('tr');
        const id = tr.getAttribute('data-id');
        try {
          btn.disabled = true;
          const res = await fetch(API_TOGGLE(id), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(CSRF ? {'X-CSRFToken': CSRF} : {})
            },
            body: JSON.stringify({})
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || 'toggle failed');
          const enabled = !!(data.flow && data.flow.enabled);
          tr.querySelector('.status').innerHTML = enabled
            ? '<span class="badge text-bg-success">Activo</span>'
            : '<span class="badge text-bg-secondary">Inactivo</span>';
          btn.textContent = enabled ? 'Desactivar' : 'Activar';
          setState('<div class="alert alert-success mb-0">Estado actualizado.</div>');
        } catch (err) {
          console.error(err);
          setState('<div class="alert alert-danger mb-0"><i class="bi bi-x-octagon me-2"></i>Error al cambiar estado.</div>');
        } finally {
          btn.disabled = false;
          setTimeout(()=> setState(''), 1600);
        }
      });
    });

    // Ejecutar ahora (requiere webhook mapeado en .env)
    rows.querySelectorAll('button[data-action="run"]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const tr = e.target.closest('tr');
        const id = tr.getAttribute('data-id');
        try {
          btn.disabled = true;
          setState('<div class="alert alert-secondary mb-0"><span class="spinner-border spinner-border-sm me-2"></span>Ejecutando…</div>');
          const res = await fetch(API_RUNNOW(id), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(CSRF ? {'X-CSRFToken': CSRF} : {})
            },
            body: JSON.stringify({source: 'admin'})
          });
          const data = await res.json();
          if (!res.ok || !data.ok) throw new Error(data.error || 'run failed');
          setState('<div class="alert alert-success mb-0">Disparado correctamente.</div>');
        } catch (err) {
          console.error(err);
          setState('<div class="alert alert-danger mb-0">No se pudo ejecutar (define webhook en .env).</div>');
        } finally {
          btn.disabled = false;
          setTimeout(()=> setState(''), 1600);
        }
      });
    });
  }

  async function load() {
    try {
      setState('<div class="alert alert-secondary mb-0"><span class="spinner-border spinner-border-sm me-2"></span>Cargando flujos…</div>');
      const res = await fetch(API_LIST, {headers: {"Accept": "application/json"}});
      if (!res.ok) throw new Error('error api');
      const flows = await res.json();
      rows.innerHTML = (flows && flows.length) ? flows.map(row).join('') : '<tr><td colspan="7">No hay flujos configurados.</td></tr>';
      bindRowActions();
      setState('');
    } catch (err) {
      console.error(err);
      rows.innerHTML = '<tr><td colspan="7">No se pudieron cargar las fuentes.</td></tr>';
      setState('<div class="alert alert-danger mb-0">Error cargando datos.</div>');
    }
  }

  load();
})();
