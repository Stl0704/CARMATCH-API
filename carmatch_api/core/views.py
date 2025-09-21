from django.shortcuts import render

# Create your views here.
# core/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


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
