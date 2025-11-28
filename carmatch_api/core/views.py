# core/views.py
from functools import wraps
from django.http import HttpResponse
import csv

from rest_framework import viewsets, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from django_filters.rest_framework import DjangoFilterBackend

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import OuterRef, Subquery, DecimalField, Q
from django.utils import timezone
from django.conf import settings

from .serializers import ProductSerializer, OfferProductSerializer
from .n8n_api import list_flows_for_admin, set_active_wf, run_now_wf, last_execution_status
from .forms import (
    LoginForm,
    UserListingForm,
    RegisterForm,
    UserAdminCreateForm,
    UserAdminUpdateForm,
)
from .models import Product, OfferProduct, User, PriceHistorical, UserListing


# =============== HELPERS DE AUTENTICACIÓN ===============

def create_user_with_password(name: str, email: str, raw_password: str, role: str = "usuario"):
    return User.objects.create(
        name=name,
        email=email.lower(),
        password_hash=make_password(raw_password),
        role=role,
    )


def get_logged_user(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None


# def admin_required(view_func):
#     @wraps(view_func)
#     def _wrapped(request, *args, **kwargs):
#         user = get_logged_user(request)
#         if not user:
#             messages.error(request, "Debes iniciar sesión.")
#             return redirect("login")
#         # Roles con permiso de administración
#         if user.role not in ("admin", "superadmin"):
#             messages.error(request, "No tienes permisos para acceder a la administración de usuarios.")
#             return redirect("dashboard")
#         # opcional: guardar el usuario actual en la request
#         request.current_user = user
#         return view_func(request, *args, **kwargs)
#     return _wrapped

def roles_required(*allowed_roles):
    """
    Decorador genérico para restringir vistas según rol.
    Ejemplo:
      @roles_required("admin")
      @roles_required("admin", "analista")
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = get_logged_user(request)
            if not user:
                messages.error(request, "Debes iniciar sesión.")
                return redirect("login")
            if user.role not in allowed_roles:
                messages.error(request, "No tienes permisos para acceder a esta sección.")
                return redirect("dashboard")
            request.current_user = user
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


# Alias concretos que vamos a usar:
admin_required = roles_required("admin")
admin_or_analista_required = roles_required("admin", "analista")


# =============== API BÁSICA ===============

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


# =============== PÁGINAS HTML PÚBLICAS / USUARIO ===============

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
                request.session["user_role"] = u.role  # 👈 guardamos el rol
                request.session.set_expiry(60 * 60 * 8)  # 8h
                messages.success(request, f"¡Bienvenido {u.name}!")
                return redirect("dashboard")
            messages.error(request, "Correo o contraseña inválidos.")
    return render(request, "login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def register_view(request):
    # Si ya está logueado, no tiene sentido registrarse de nuevo
    if request.session.get("user_id"):
        messages.info(request, "Ya tienes una sesión activa.")
        return redirect("dashboard")

    form = RegisterForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        name = form.cleaned_data["name"].strip()
        email = form.cleaned_data["email"].strip().lower()
        password = form.cleaned_data["password"]

        create_user_with_password(
            name=name,
            email=email,
            raw_password=password,
            role="usuario",
        )

        messages.success(
            request,
            "Tu cuenta ha sido creada correctamente. Ahora puedes iniciar sesión."
        )
        return redirect("login")

    return render(request, "registrarse.html", {"form": form})


def logout_view(request):
    request.session.flush()
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect("login")


def dashboard_view(request):
    user_id = request.session.get("user_id")
    user_name = request.session.get("user_name")

    # Publicaciones recientes del usuario (máx. 5)
    user_listings = UserListing.objects.none()
    if user_id:
        user_listings = (
            UserListing.objects
            .filter(user_id=user_id)
            .order_by("-created_at")[:5]
        )

    # Top 5 ofertas (con último precio si existe)
    latest_price_sq = PriceHistorical.objects.filter(
        offer=OuterRef("pk")
    ).order_by("-valid_at").values("price")[:1]

    top_offers = (
        OfferProduct.objects
        .select_related("product", "store")
        .annotate(
            latest_price=Subquery(
                latest_price_sq,
                output_field=DecimalField(max_digits=14, decimal_places=2)
            )
        )
        .order_by("-created_at")[:5]
    )

    context = {
        "user_name": user_name,
        "listings": user_listings,
        "top_offers": top_offers,
    }
    return render(request, "dashboard.html", context)


@require_http_methods(["GET", "POST"])
def user_listings_view(request):
    # Verificamos sesión (simple, como tu login actual)
    user_id = request.session.get("user_id")
    if not user_id:
        messages.warning(request, "Debes iniciar sesión para publicar.")
        return redirect("login")

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        request.session.flush()
        messages.error(request, "Sesión inválida, vuelve a iniciar sesión.")
        return redirect("login")

    if request.method == "POST":
        form = UserListingForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.user = user
            listing.save()
            messages.success(request, "Publicación creada correctamente.")
            return redirect("user_listings")
    else:
        form = UserListingForm()

    publicaciones = UserListing.objects.filter(user=user).order_by("-created_at")

    return render(
        request,
        "publicar.html",
        {
            "form": form,
            "publicaciones": publicaciones,
            "user_name": request.session.get("user_name"),
        },
    )


def ofertas_page(request):
    # Renderiza plantilla que consulta /api/ofertas/
    return render(request, "ofertas.html")


# =============== VIEWSETS API (PRODUCTOS / OFERTAS) ===============

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().select_related('category', 'brand').prefetch_related('specifications')
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

    queryset = (
        OfferProduct.objects
        .select_related('product', 'store')
        .annotate(
            latest_price=Subquery(
                latest_price_sq,
                output_field=DecimalField(max_digits=14, decimal_places=2)
            )
        )
        .all()
    )
    serializer_class = OfferProductSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['store', 'product', 'product__brand', 'product__category']
    search_fields = ['product__name', 'product__sku', 'store__name']
    ordering_fields = ['created_at']


# =============== ADMIN: PÁGINAS HTML GENERALES ===============

@admin_or_analista_required
def admin_home(request):
    """Dashboard de administración."""
    return render(request, "administracion.html")


@admin_required
@ensure_csrf_cookie
def admin_fuentes_page(request):
    """Pantalla: Fuentes WebScrapping (real n8n)."""
    return render(request, "admin_fuentes.html", {
        "n8n_base": getattr(settings, "N8N_BASE_URL", ""),
    })


@admin_or_analista_required
def admin_reports_page(request):
    """
    Pantalla de reportes con opciones para descargar:
      - Inventario (productos)
      - Publicaciones (UserListing)
      - Ofertas (OfferProduct)
    """
    return render(request, "reportes.html")

@admin_or_analista_required
def export_inventory_excel(request):
    """
    Exporta el catálogo de productos como CSV (Excel lo abre sin problema).
    """
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="inventario_carmatch.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "ID",
        "Nombre",
        "SKU",
        "Categoría",
        "Marca",
        "Garantía (meses)",
        "Creado",
    ])

    productos = (
        Product.objects
        .select_related("category", "brand")
        .order_by("id")
    )

    for p in productos:
        writer.writerow([
            p.id,
            p.name,
            getattr(p, "sku", ""),
            getattr(p.category, "name", "") if p.category_id else "",
            getattr(p.brand, "name", "") if p.brand_id else "",
            getattr(p, "warranty_months", ""),
            p.created_at.astimezone(timezone.get_current_timezone()).strftime("%Y-%m-%d %H:%M")
            if p.created_at else "",
        ])

    return response

@admin_or_analista_required
def export_publicaciones_excel(request):
    """
    Exporta las publicaciones de los usuarios como CSV.
    """
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="publicaciones_carmatch.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "ID",
        "Título",
        "Descripción",
        "Categoría",
        "Stock",
        "Precio",
        "Usuario",
        "Fecha creación",
    ])

    publicaciones = (
        UserListing.objects
        .select_related("category", "user")
        .order_by("-created_at")
    )

    for pub in publicaciones:
        writer.writerow([
            pub.id,
            pub.title,
            pub.description.replace("\n", " ") if pub.description else "",
            getattr(pub.category, "name", "") if pub.category_id else "",
            pub.stock,
            pub.price,
            getattr(pub.user, "name", "") if pub.user_id else "",
            pub.created_at.astimezone(timezone.get_current_timezone()).strftime("%Y-%m-%d %H:%M")
            if pub.created_at else "",
        ])

    return response

@admin_or_analista_required
def export_ofertas_excel(request):
    """
    Exporta las ofertas con su último precio registrado.
    """
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="ofertas_carmatch.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "ID oferta",
        "Producto",
        "Tienda",
        "Último precio",
        "Fecha última actualización precio",
        "Fecha creación oferta",
    ])

    # Subquery para último precio
    latest_price_sq = PriceHistorical.objects.filter(
        offer=OuterRef("pk")
    ).order_by("-valid_at").values("price")[:1]

    latest_date_sq = PriceHistorical.objects.filter(
        offer=OuterRef("pk")
    ).order_by("-valid_at").values("valid_at")[:1]

    ofertas = (
        OfferProduct.objects
        .select_related("product", "store")
        .annotate(
            latest_price=Subquery(
                latest_price_sq,
                output_field=DecimalField(max_digits=14, decimal_places=2)
            ),
            latest_valid_at=Subquery(latest_date_sq)
        )
        .order_by("-created_at")
    )

    tz = timezone.get_current_timezone()

    for o in ofertas:
        # Convertir fecha del último precio si existe
        if o.latest_valid_at:
            last_date = o.latest_valid_at.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        else:
            last_date = ""

        created_str = (
            o.created_at.astimezone(tz).strftime("%Y-%m-%d %H:%M")
            if o.created_at else ""
        )

        writer.writerow([
            o.id,
            getattr(o.product, "name", "") if o.product_id else "",
            getattr(o.store, "name", "") if o.store_id else "",
            o.latest_price if o.latest_price is not None else "",
            last_date,
            created_str,
        ])

    return response

# =============== ADMIN: USUARIOS ===============

@admin_required
def admin_user_list(request):
    q = request.GET.get("q", "").strip()
    users = User.objects.all().order_by("-created_at")
    if q:
        users = users.filter(
            Q(name__icontains=q) |
            Q(email__icontains=q) |
            Q(role__icontains=q)
        )

    return render(request, "admin_user_list.html", {
        "users": users,
        "query": q,
    })


@admin_required
@require_http_methods(["GET", "POST"])
def admin_user_create(request):
    if request.method == "POST":
        form = UserAdminCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data["password"]
            user.password_hash = make_password(password)
            user.email = user.email.lower().strip()
            user.save()
            messages.success(request, "Usuario creado correctamente.")
            return redirect("admin_user_list")
    else:
        form = UserAdminCreateForm()

    return render(request, "admin_user_form.html", {
        "form": form,
        "is_edit": False,
    })


@admin_required
@require_http_methods(["GET", "POST"])
def admin_user_edit(request, user_id):
    user_obj = get_object_or_404(User, pk=user_id)

    if request.method == "POST":
        form = UserAdminUpdateForm(request.POST, instance=user_obj)
        if form.is_valid():
            user = form.save(commit=False)
            new_password = form.cleaned_data.get("new_password")
            if new_password:
                user.password_hash = make_password(new_password)
            user.email = user.email.lower().strip()
            user.save()
            messages.success(request, "Usuario actualizado correctamente.")
            return redirect("admin_user_list")
    else:
        form = UserAdminUpdateForm(instance=user_obj)

    return render(request, "admin_user_form.html", {
        "form": form,
        "is_edit": True,
        "user_obj": user_obj,
    })


@admin_required
@require_http_methods(["GET", "POST"])
def admin_user_delete(request, user_id):
    user_obj = get_object_or_404(User, pk=user_id)

    # Opcional: evitar que un admin se borre a sí mismo
    logged = get_logged_user(request)
    if logged and logged.id == user_obj.id:
        messages.error(request, "No puedes eliminar tu propio usuario desde aquí.")
        return redirect("admin_user_list")

    if request.method == "POST":
        user_obj.delete()
        messages.success(request, "Usuario eliminado correctamente.")
        return redirect("admin_user_list")

    return render(request, "admin_user_confirm_delete.html", {
        "user_obj": user_obj,
    })


# =============== ADMIN: API MOCK n8n (estructura base, por si la usas) ===============

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


# =============== PÁGINA CHAT IA (FRONT) ===============

def ai_chat_page(request):
    """Pantalla visual del chat de IA (sin backend)."""
    return render(request, "ai_chat.html")


# =============== API REAL n8n ===============

@api_view(["GET"])
@permission_classes([AllowAny])
def n8n_flows(request):
    return Response(list_flows_for_admin())


@api_view(["POST"])
@permission_classes([AllowAny])
def n8n_toggle_flow(request, flow_id: str):
    desired = request.data.get("enabled")
    if desired is None:
        current = next(
            (f for f in list_flows_for_admin() if str(f["id"]) == str(flow_id)),
            None,
        )
        desired = not bool(current and current.get("enabled"))
    data = set_active_wf(flow_id, bool(desired))
    return Response(
        {"ok": True, "flow": {"id": data.get("id"), "enabled": data.get("active")}}
    )


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
    return Response(
        {"ok": res["ok"], "status": res["status"], "message": msg, "details": details},
        status=200 if res["ok"] else 400,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def n8n_last_exec_view(request, flow_id: str):
    data = last_execution_status(flow_id)
    return Response(
        data,
        status=200 if data.get("ok") in (True, False) else 400,
    )
