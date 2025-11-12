from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from core.views import (
    login_view, logout_view, dashboard_view, repuestos_page, ofertas_page,
    admin_home, admin_fuentes_page, ai_chat_page  # <-- NUEVO
)

def root_api(_request):
    return JsonResponse({
        "name": "carmatch-api",
        "version": "v1",
        "endpoints": ["/api/ping/", "/api/repuestos-data/", "/api/ofertas/", "/api/n8n/flows/"]
    })

urlpatterns = [
    path("", root_api),

    # Páginas HTML
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("repuestos/", repuestos_page, name="repuestos_page"),
    path("ofertas/", ofertas_page, name="ofertas_page"),
    path("admin/", admin_home, name="admin_home"),                     # <-- NUEVO
    path("admin/fuentes/", admin_fuentes_page, name="admin_fuentes"),
    path("ai/", ai_chat_page, name="ai_chat"),# <-- NUEVO

    # API
    path("api/", include("core.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
