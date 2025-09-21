# carmatch_api/urls.py (RAÍZ)
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def root_api(_request):
    # Root responde JSON para que se note que es una API
    return JsonResponse({
        "name": "carmatch-api",
        "version": "v1",
        "endpoints": ["/api/ping/", "/api/repuestos/"]
    })


urlpatterns = [
    # GET / -> JSON (no página HTML de Django)
    path("", root_api),
    # prefijo /api para todos los endpoints
    path("api/", include("core.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"),
         name="swagger-ui"),

]
