# core/urls.py
from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import (
    ping, RepuestosViewSet, login_view, logout_view,
    ProductViewSet, OfferProductViewSet,
    n8n_flows, n8n_toggle_flow, n8n_run_now_view,
    admin_fuentes_page, user_listings_view, register_view,
    admin_user_list, admin_user_create, admin_user_edit, admin_user_delete,
    dashboard_view,admin_home,
    admin_reports_page,  # 👈 NUEVO
    export_inventory_excel,  # 👈 NUEVO
    export_publicaciones_excel,  # 👈 NUEVO
    export_ofertas_excel,  # 👈 NUEVO
)

router = SimpleRouter()
router.register(r"repuestos-data", RepuestosViewSet, basename="repuestos-data")
router.register(r"productos", ProductViewSet, basename="productos")
router.register(r"ofertas", OfferProductViewSet, basename="ofertas")


urlpatterns = [
    path("ping/", ping, name="ping"),
    path("", include(router.urls)),

    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/", dashboard_view, name="dashboard"),

    path("admin/", admin_home, name="admin_home"),
    path("admin/fuentes/", admin_fuentes_page, name="admin_fuentes"),

    path("admin/usuarios/", admin_user_list, name="admin_user_list"),
    path("admin/usuarios/nuevo/", admin_user_create, name="admin_user_create"),
    path("admin/usuarios/<int:user_id>/editar/", admin_user_edit, name="admin_user_edit"),
    path("admin/usuarios/<int:user_id>/eliminar/", admin_user_delete, name="admin_user_delete"),

    path("n8n/flows/", n8n_flows, name="n8n_flows"),
    path("n8n/flows/<slug:flow_id>/toggle/", n8n_toggle_flow, name="n8n_toggle_flow"),
    path("n8n/flows/<slug:flow_id>/run-now/", n8n_run_now_view, name="n8n_run_now_flow"),

    path("mis-publicaciones/", user_listings_view, name="user_listings"),
    path("registrarse/", register_view, name="register"),
    
    path("admin/reportes/", admin_reports_page, name="admin_reports"),

    path("admin/reportes/inventario.xlsx", export_inventory_excel, name="admin_report_inventory"),
    path("admin/reportes/publicaciones.xlsx", export_publicaciones_excel, name="admin_report_publicaciones"),
    path("admin/reportes/ofertas.xlsx", export_ofertas_excel, name="admin_report_ofertas"),
]
