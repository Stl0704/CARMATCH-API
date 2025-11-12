# core/n8n_api.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

# =========================
#  Config desde settings.py
# =========================
API: str        = getattr(settings, "N8N_API_URL", "")
KEY: str        = getattr(settings, "N8N_API_KEY", "")
BASE: str       = getattr(settings, "N8N_BASE_URL", "")
PROJECT_ID: str = getattr(settings, "N8N_PROJECT_ID", "")

# Un único ID (compatibilidad hacia atrás; puede estar vacío)
WFID_SINGLE: str = str(getattr(settings, "N8N_WORKFLOW_ID", "") or "")

# Lista de flujos para el admin (si no se define, usa el single si existe)
FLOW_IDS: List[str] = getattr(settings, "N8N_FLOW_IDS", []) or (
    [WFID_SINGLE] if WFID_SINGLE else []
)

# Webhooks por workflowId para "Ejecutar ahora"
# Ej: {"XeE1r9jt7Z6Sdghb": "http://localhost:5678/webhook/mi-flujo/sync?token=XYZ"}
WEBHOOKS: Dict[str, str] = getattr(settings, "N8N_WEBHOOKS", {}) or {}


# =========================
#  Helpers HTTP
# =========================
def _hdr() -> Dict[str, str]:
    """
    Tu instancia n8n exige 'X-N8N-API-KEY'. Si usas Projects, se envía 'n8n-project-id'.
    """
    if not KEY:
        raise RuntimeError("Falta N8N_API_KEY en settings/env")
    headers = {
        "X-N8N-API-KEY": KEY,
    }
    if PROJECT_ID:
        headers["n8n-project-id"] = PROJECT_ID
    return headers


def _require_api():
    if not API:
        raise RuntimeError("Falta N8N_API_URL en settings/env")


def _require_single():
    if not (API and KEY and WFID_SINGLE):
        raise RuntimeError(
            "Config n8n incompleta (N8N_API_URL / N8N_API_KEY / N8N_WORKFLOW_ID)"
        )


def _editor_url(wfid: str | int) -> str:
    return f"{BASE}/workflow/{wfid}" if BASE else ""


# =========================
#  Operaciones por workflow
# =========================
def get_workflow(wfid: str | int) -> Dict[str, Any]:
    _require_api()
    r = requests.get(f"{API}/workflows/{wfid}", headers=_hdr(), timeout=20)
    r.raise_for_status()
    return r.json()


def set_active_wf(wfid: str | int, active: bool) -> Dict[str, Any]:
    _require_api()
    r = requests.patch(
        f"{API}/workflows/{wfid}",
        json={"active": bool(active)},
        headers=_hdr(),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def last_execution(wfid: str | int) -> Optional[Dict[str, Any]]:
    """
    Devuelve la última ejecución del workflow (si existe).
    n8n <= 1.x devuelve 'data' o 'items'; tomamos el primero si hay.
    """
    _require_api()
    r = requests.get(
        f"{API}/executions",
        params={"workflowId": wfid, "limit": 1},
        headers=_hdr(),
        timeout=20,
    )
    r.raise_for_status()
    data = r.json() or {}
    items = data.get("data") or data.get("items") or []
    return items[0] if items else None


def run_now_wf(wfid: str | int, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Dispara el webhook del workflow (si está mapeado en settings.N8N_WEBHOOKS).
    Retorna: { ok(bool), status(int), body(dict|str) }.
    - Si el webhook es "sync" (wait for completion), tendrás la salida del flujo.
    - Si es async, verás el HTTP de n8n; luego puedes consultar last_execution().
    """
    url = WEBHOOKS.get(str(wfid))
    if not url:
        return {"ok": False, "status": 400, "error": "No webhook configured for this workflow"}

    r = requests.post(url, json=payload or {}, timeout=90)
    content_type = r.headers.get("content-type", "")
    try:
        body = r.json() if content_type.startswith("application/json") else r.text
    except Exception:
        body = r.text

    return {"ok": r.ok, "status": r.status_code, "body": body}


def last_execution_status(wfid: str | int) -> Dict[str, Any]:
    """
    Devuelve estado de la última ejecución (success/error/unknown) y metadatos.
    Pensado para mostrar un modal/post-ejecución en tu admin.
    """
    try:
        le = last_execution(wfid)
    except Exception as e:
        return {"ok": False, "status": "unknown", "error": str(e)}

    if not le:
        return {"ok": False, "status": "unknown"}

    # n8n modernos devuelven 'status' (success/error/running/canceled)
    status = (le.get("status") or "").lower()
    if not status:
        # fallback para n8n viejos
        status = "success" if le.get("finished") else "error"

    out = {
        "ok": status == "success",
        "status": status,
        "id": le.get("id"),
        "startedAt": le.get("startedAt"),
        "stoppedAt": le.get("stoppedAt"),
        "workflowId": le.get("workflowId"),
        "error": le.get("error") or "",
    }
    return out


# =========================
#  Listado para la UI admin
# =========================
def list_flows_for_admin() -> List[Dict[str, Any]]:
    """
    Devuelve los flujos definidos en FLOW_IDS con metadatos mínimos
    para pintar la tabla del admin.
    """
    flows: List[Dict[str, Any]] = []
    for wfid in FLOW_IDS:
        if not wfid:
            continue
        try:
            w  = get_workflow(wfid)
            le = last_execution(wfid)
            flows.append(
                {
                    "id": w.get("id"),
                    "name": w.get("name"),
                    "enabled": bool(w.get("active")),
                    "last_run": (le or {}).get("startedAt") or (le or {}).get("finishedAt"),
                    "n8n_url": _editor_url(w.get("id")),
                    # placeholders (si luego quieres parsear un Cron node)
                    "schedule_time": "",
                    "frequency": "",
                    "has_webhook": str(w.get("id")) in WEBHOOKS,
                }
            )
        except Exception:
            # Si un flujo falla, seguimos con los demás
            continue
    return flows


# =========================
#  Modo "single" (compat)
# =========================
def get_workflow_single() -> Dict[str, Any]:
    """Usa N8N_WORKFLOW_ID único (compat si te sirve en otros endpoints)."""
    _require_single()
    r = requests.get(f"{API}/workflows/{WFID_SINGLE}", headers=_hdr(), timeout=20)
    r.raise_for_status()
    return r.json()


def set_active_single(active: bool) -> Dict[str, Any]:
    _require_single()
    r = requests.patch(
        f"{API}/workflows/{WFID_SINGLE}",
        json={"active": bool(active)},
        headers=_hdr(),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def list_executions_single(limit: int = 20) -> Dict[str, Any]:
    _require_single()
    r = requests.get(
        f"{API}/executions",
        params={"workflowId": WFID_SINGLE, "limit": limit},
        headers=_hdr(),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def editor_url_single() -> str:
    if not (BASE and WFID_SINGLE):
        raise RuntimeError("Falta N8N_BASE_URL o N8N_WORKFLOW_ID")
    return _editor_url(WFID_SINGLE)


def update_workflow_json_single(new_json: dict) -> Dict[str, Any]:
    """⚠️ PUT reemplaza el workflow completo en n8n; úsalo con cuidado."""
    _require_single()
    r = requests.put(
        f"{API}/workflows/{WFID_SINGLE}",
        json=new_json,
        headers=_hdr(),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def run_now_single(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Ejecuta el único flujo usando un webhook "global".
    (Si prefieres por-ID, usa run_now_wf).
    """
    url = WEBHOOKS.get(WFID_SINGLE) or getattr(settings, "N8N_WEBHOOK_URL", "")
    if not url:
        return {"ok": False, "error": "No webhook configured (N8N_WEBHOOKS o N8N_WEBHOOK_URL)"}
    r = requests.post(url, json=payload or {}, timeout=90)
    content_type = r.headers.get("content-type", "")
    try:
        body = r.json() if content_type.startswith("application/json") else r.text
    except Exception:
        body = r.text
    return {"ok": r.ok, "status": r.status_code, "body": body}
