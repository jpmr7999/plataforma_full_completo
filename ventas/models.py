from django.db import models
from django.utils import timezone

class ProductoCasaMatriz(models.Model):
    nombre = models.CharField(max_length=100)
    cantidad = models.PositiveIntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)

class Venta(models.Model):
    nombre_producto = models.CharField(max_length=100)
    sucursal = models.CharField(max_length=100)
    cantidad = models.PositiveIntegerField()
    total_clp = models.DecimalField(max_digits=12, decimal_places=2)
    total_usd = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.CharField(max_length=10,default=timezone.now)

    
    nombre_comprador = models.CharField(max_length=100, blank=True, null=True)

class Sucursal(models.Model):
    id_sucursal = models.PositiveIntegerField(max_length=50)
    nombre_sucursal = models.PositiveBigIntegerField(max_length=100)
    unidades = models.PositiveIntegerField()
    precio = models.DecimalField(max_digits=12,decimal_places=2)
