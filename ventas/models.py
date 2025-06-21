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

class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "email": self.email,
            "telefono": self.telefono,
            "direccion": self.direccion,
            "fecha_registro": self.fecha_registro.isoformat(),
            "activo": self.activo
        }