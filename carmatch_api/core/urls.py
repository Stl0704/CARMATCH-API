# core/urls.py
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
    ping, RepuestosViewSet, login_view, logout_view,
    ProductViewSet, OfferProductViewSet,
    n8n_flows, n8n_toggle_flow, n8n_run_now_view,
    admin_fuentes_page,# <-- NUEVO
)

router = SimpleRouter()
router.register(r"repuestos-data", RepuestosViewSet, basename="repuestos-data")
router.register(r"productos", ProductViewSet, basename="productos")
router.register(r"ofertas", OfferProductViewSet, basename="ofertas")

urlpatterns = [
    path("ping/", ping, name="ping"),
    path("", include(router.urls)),

    # (opcional) login/logout aquí si los quieres bajo /api/
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("admin/fuentes/", admin_fuentes_page, name="admin_fuentes"),
    
    path("n8n/flows/", n8n_flows, name="n8n_flows"),
    path("n8n/flows/<slug:flow_id>/toggle/", n8n_toggle_flow, name="n8n_toggle_flow"),
    path("n8n/flows/<slug:flow_id>/run-now/", n8n_run_now_view, name="n8n_run_now_flow"),
]
