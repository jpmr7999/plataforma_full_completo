from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'clientes', views.ClienteViewSet)

urlpatterns = [
    path('', views.vista_venta, name='vista_venta'),
    path('historial/', views.historial_ventas, name='historial_ventas'),
    path('pago/', views.pagina_pago, name='pagina_pago'),
    path('webpay/return/', views.webpay_return, name='webpay_return'),
    path('inventario/', views.inventario, name='inventario'),
    path('actualizar-stock/', views.actualizar_stock, name='actualizar_stock'),
    path('api/', include(router.urls)),
]
