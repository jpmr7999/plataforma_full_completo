from django.urls import path
from . import views

urlpatterns = [
    path('', views.vista_venta, name='vista_venta'),
    path('historial/', views.historial_ventas, name='historial_ventas'),
]
