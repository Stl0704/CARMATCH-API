# core/views.py
from rest_framework.decorators import api_view
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from .serializers import ProductSerializer, OfferProductSerializer

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from .n8n_api import list_flows_for_admin, set_active_wf, run_now_wf,last_execution_status

from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import OuterRef,Subquery,DecimalField
from django.utils import timezone
from django.conf import settings

from .forms import LoginForm
from .models import Product, OfferProduct,User,PriceHistorical
# ---------- API ----------
@api_view(["GET"])
def ping(request):
    return Response({"service": "carmatch-api", "status": "ok"})

class RepuestosViewSet(ViewSet):
    def list(self, request):
        data = [
            {"id": 1, "nombre": "Filtro de aceite", "precio": 5990},
            {"id": 2, "nombre": "Bujía", "precio": 3990},
        ]
        return Response(data)

# ---------- PÁGINAS ----------
def repuestos_page(request):
    # HTML que consume el API /api/repuestos-data/ vía fetch
    return render(request, "repuestos.html")

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.session.get("user_id"):
        return redirect("dashboard")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        password = form.cleaned_data["password"]
        try:
            u = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Correo o contraseña inválidos.")
        else:
            if check_password(password, u.password_hash):
                request.session["user_id"] = u.id
                request.session["user_name"] = u.name
                request.session.set_expiry(60 * 60 * 8)  # 8h
                messages.success(request, f"¡Bienvenido {u.name}!")
                return redirect("dashboard")
            messages.error(request, "Correo o contraseña inválidos.")
    return render(request, "login.html", {"form": form})

def logout_view(request):
    request.session.flush()
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect("login")

def create_user_with_password(name: str, email: str, raw_password: str, role: str = "usuario"):
    return User.objects.create(
        name=name, email=email.lower(), password_hash=make_password(raw_password), role=role
    )

def dashboard_view(request):
    return render(request, "dashboard.html", {"user_name": request.session.get("user_name")})


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().select_related('category','brand').prefetch_related('specifications')
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'brand', 'warranty_months']
    search_fields = ['name', 'sku', 'specifications__key', 'specifications__value']
    ordering_fields = ['created_at', 'name']

class OfferProductViewSet(viewsets.ModelViewSet):
    # Subquery para último precio
    latest_price_sq = PriceHistorical.objects.filter(
        offer=OuterRef('pk')
    ).order_by('-valid_at').values('price')[:1]

    queryset = (OfferProduct.objects
        .select_related('product','store')
        .annotate(latest_price=Subquery(latest_price_sq, output_field=DecimalField(max_digits=14, decimal_places=2)))
        .all()
    )
    serializer_class = OfferProductSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['store', 'product', 'product__brand', 'product__category']
    search_fields   = ['product__name', 'product__sku', 'store__name']
    ordering_fields = ['created_at']
    
def ofertas_page(request):
        # Renderiza plantilla que consulta /api/ofertas/
    return render(request, "ofertas.html")


# =========================
#  ADMIN: PÁGINAS HTML
# =========================
def admin_home(request):
    """Dashboard de administración."""
    return render(request, "administracion.html")

@ensure_csrf_cookie
def admin_fuentes_page(request):
    """Pantalla: Fuentes WebScrapping (real n8n)."""
    return render(request, "admin_fuentes.html", {
        "n8n_base": getattr(settings, "N8N_BASE_URL", ""),
    })

# =========================
#  ADMIN: API MOCK n8n
# =========================
MOCK_FLOWS = [
    {
        "id": 101,
        "name": "Autoplanet — Scrape neumáticos",
        "enabled": True,
        "last_run": (timezone.now() - timezone.timedelta(hours=3)).isoformat(),
        "schedule_cron": "0 4 * * *",          # 04:00 todos los días
        "schedule_time": "04:00",
        "frequency": "Todos los días",
        "n8n_url": "https://n8n.mi-dominio.tld/workflow/101",
    },
    {
        "id": 102,
        "name": "MercadoLibre — Scrape repuestos",
        "enabled": False,
        "last_run": (timezone.now() - timezone.timedelta(days=1, hours=2)).isoformat(),
        "schedule_cron": "0 4 * * *",
        "schedule_time": "04:00",
        "frequency": "Todos los días",
        "n8n_url": "https://n8n.mi-dominio.tld/workflow/102",
    },
    {
        "id": 103,
        "name": "Neumarket — Scrape llantas",
        "enabled": True,
        "last_run": (timezone.now() - timezone.timedelta(minutes=45)).isoformat(),
        "schedule_cron": "0 4 * * *",
        "schedule_time": "04:00",
        "frequency": "Todos los días",
        "n8n_url": "https://n8n.mi-dominio.tld/workflow/103",
    },
]

def _get_flow(flow_id: int):
    for f in MOCK_FLOWS:
        if f["id"] == flow_id:
            return f
    return None

@api_view(["GET"])
def n8n_flows(request):
    return Response(list_flows_for_admin())

@api_view(["POST"])
def n8n_toggle_flow(request, flow_id: str):
    desired = request.data.get("enabled")
    if desired is None:
        current = next((f for f in list_flows_for_admin() if str(f["id"]) == str(flow_id)), None)
        desired = not bool(current and current.get("enabled"))
    data = set_active_wf(flow_id, bool(desired))
    return Response({"ok": True, "flow": {"id": data.get("id"), "enabled": data.get("active")}})

def ai_chat_page(request):
    """Pantalla visual del chat de IA (sin backend)."""
    return render(request, "ai_chat.html")


@api_view(["GET"])
@permission_classes([AllowAny])
def n8n_flows(request):
    return Response(list_flows_for_admin())

@api_view(["POST"])
@permission_classes([AllowAny])
def n8n_toggle_flow(request, flow_id: str):
    desired = request.data.get("enabled")
    if desired is None:
        current = next((f for f in list_flows_for_admin() if str(f["id"]) == str(flow_id)), None)
        desired = not bool(current and current.get("enabled"))
    data = set_active_wf(flow_id, bool(desired))
    return Response({"ok": True, "flow": {"id": data.get("id"), "enabled": data.get("active")}})

@api_view(["POST"])
@permission_classes([AllowAny])
def n8n_run_now_view(request, flow_id: str):
    payload = request.data if isinstance(request.data, dict) else {}
    res = run_now_wf(flow_id, payload)
    # Unificamos a {ok, status, message, details}
    body = res.get("body")
    if isinstance(body, dict):
        msg = body.get("message") or body.get("msg") or body.get("status") or "Ejecución enviada"
        details = body
    else:
        msg = "Ejecución enviada" if res["ok"] else "Error al ejecutar"
        details = {"raw": body}
    return Response({"ok": res["ok"], "status": res["status"], "message": msg, "details": details}, status=200 if res["ok"] else 400)

@api_view(["GET"])
@permission_classes([AllowAny])
def n8n_last_exec_view(request, flow_id: str):
    data = last_execution_status(flow_id)
    return Response(data, status=200 if data.get("ok") in (True, False) else 400)