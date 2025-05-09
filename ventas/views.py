from django.shortcuts import render, redirect
from .models import ProductoCasaMatriz, Venta
from django.contrib import messages

def obtener_sucursales_api():
    return [
        {"id": 1, "nombre": "Sucursal 1", "cantidad": 31, "precio": 333},
        {"id": 2, "nombre": "Sucursal 2", "cantidad": 23, "precio": 222},
        {"id": 3, "nombre": "Sucursal 3", "cantidad": 100, "precio": 1111},
    ]

def obtener_valor_dolar():
    return 900  # valor fijo simulado

def vista_venta(request):
    productos = ProductoCasaMatriz.objects.all()
    sucursales = obtener_sucursales_api()
    total = total_usd = 0

    if request.method == "POST":
        sucursal_id = request.POST.get("sucursal")
        cantidad = int(request.POST.get("cantidad"))

        sucursal = next((s for s in sucursales if str(s["id"]) == sucursal_id), None)

        if sucursal and cantidad <= sucursal["cantidad"]:
            precio = sucursal["precio"]
        else:
            producto_matriz = ProductoCasaMatriz.objects.first()
            if not producto_matriz or cantidad > producto_matriz.cantidad:
                messages.error(request, "No hay suficiente stock.")
                return redirect("vista_venta")
            precio = float(producto_matriz.precio)
            sucursal = {"nombre": "Casa Matriz"}

        total = cantidad * precio
        total_usd = round(total / obtener_valor_dolar(), 2)

        Venta.objects.create(
            nombre_producto="Producto X",
            sucursal=sucursal["nombre"],
            cantidad=cantidad,
            total_clp=total,
            total_usd=total_usd
        )

        if sucursal["nombre"] == "Casa Matriz":
            producto_matriz.cantidad -= cantidad
            producto_matriz.save()

        messages.success(request, f"Venta registrada: ${total} CLP / ${total_usd} USD")

    return render(request, "ventas/venta.html", {
        "productos": productos,
        "sucursales": sucursales,
        "total": total,
        "total_usd": total_usd
    })

def historial_ventas(request):
    ventas = Venta.objects.order_by('-fecha')
    return render(request, "ventas/historial.html", {"ventas": ventas})
