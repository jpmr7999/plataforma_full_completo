from django.db import models
from django.utils import timezone

class ProductoCasaMatriz(models.Model):
    nombre = models.CharField(max_length=100)
    cantidad = models.PositiveIntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)

class Sucursal(models.Model):
    nombre = models.CharField(max_length=100)
    cantidad = models.PositiveIntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "cantidad": self.cantidad,
            "precio": float(self.precio)
        }

class Venta(models.Model):
    nombre_producto = models.CharField(max_length=100)
    sucursal = models.CharField(max_length=100)
    sucursal_id = models.IntegerField(null=True, blank=True)
    cantidad = models.PositiveIntegerField()
    total_clp = models.DecimalField(max_digits=12, decimal_places=2)
    total_usd = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.CharField(max_length=10,default=timezone.now)
    pagada = models.BooleanField(default=False)
    nombre_comprador = models.CharField(max_length=100, blank=True, null=True)
    apellido_comprador = models.CharField(max_length=100, blank=True, null=True)
    buy_order = models.CharField(max_length=100, blank=True, null=True)  # Para Webpay