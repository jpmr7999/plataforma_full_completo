from django.shortcuts import render, redirect
from .models import ProductoCasaMatriz, Venta, Sucursal
from django.contrib import messages
from django.db.models import F
from django.http import JsonResponse
from transbank.webpay.webpay_plus.transaction import Transaction, WebpayOptions
from transbank.common.integration_type import IntegrationType
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import random

# Configuración de credenciales de prueba de Transbank
COMMERCE_CODE = "597055555532"
API_KEY = "579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C"

def inicializar_sucursales():
    if not Sucursal.objects.exists():
        sucursales_iniciales = [
            {"nombre": "Sucursal 1", "cantidad": 31, "precio": 333},
            {"nombre": "Sucursal 2", "cantidad": 23, "precio": 222},
            {"nombre": "Sucursal 3", "cantidad": 100, "precio": 1111},
        ]
        for sucursal_data in sucursales_iniciales:
            Sucursal.objects.create(**sucursal_data)

def obtener_sucursales():
    inicializar_sucursales()
    return [sucursal.to_dict() for sucursal in Sucursal.objects.all()]

def obtener_valor_dolar():
    return 900  # valor fijo simulado

def vista_venta(request):
    productos = ProductoCasaMatriz.objects.all()
    sucursales = obtener_sucursales()
    total = total_usd = 0
    stock_actualizado = None

    if request.method == "POST":
        sucursal_id = request.POST.get("sucursal")
        cantidad = int(request.POST.get("cantidad"))

        sucursal = next((s for s in sucursales if str(s["id"]) == sucursal_id), None)

        if sucursal:
            # Verificar stock disponible sin descontarlo aún
            if sucursal and cantidad <= sucursal["cantidad"]:
                precio = sucursal["precio"]
                total = cantidad * precio
                total_usd = round(total / obtener_valor_dolar(), 2)

                # Crear venta pendiente de pago
                Venta.objects.create(
                    nombre_producto="Producto X",
                    sucursal=sucursal["nombre"],
                    sucursal_id=sucursal["id"],  # Guardamos el ID de la sucursal
                    cantidad=cantidad,
                    total_clp=total,
                    total_usd=total_usd,
                    pagada=False
                )

                messages.success(request, f"Venta registrada: ${total} CLP / ${total_usd} USD")
            else:
                messages.error(request, "No hay suficiente stock.")
                return redirect("vista_venta")
        else:
            # Caso Casa Matriz
            producto_matriz = ProductoCasaMatriz.objects.first()
            if not producto_matriz or cantidad > producto_matriz.cantidad:
                messages.error(request, "No hay suficiente stock.")
                return redirect("vista_venta")
            
            precio = float(producto_matriz.precio)
            total = cantidad * precio
            total_usd = round(total / obtener_valor_dolar(), 2)

            Venta.objects.create(
                nombre_producto="Producto X",
                sucursal="Casa Matriz",
                cantidad=cantidad,
                total_clp=total,
                total_usd=total_usd,
                pagada=False
            )

            messages.success(request, f"Venta registrada: ${total} CLP / ${total_usd} USD")

    return render(request, "ventas/venta.html", {
        "productos": productos,
        "sucursales": sucursales,
        "total": total,
        "total_usd": total_usd,
        "stock_actualizado": stock_actualizado
    })

def historial_ventas(request):
    ventas = Venta.objects.order_by('-fecha')
    return render(request, "ventas/historial.html", {"ventas": ventas})

def pagina_pago(request):
    try:
        # Obtener la última venta no pagada
        venta = Venta.objects.filter(pagada=False).latest('id')
        
        # Configurar las opciones de Webpay
        tx = Transaction(WebpayOptions(commerce_code=COMMERCE_CODE, 
                                     api_key=API_KEY, 
                                     integration_type=IntegrationType.TEST))
        
        # Crear una orden de compra única
        buy_order = f"ORDEN_{venta.id}_{random.randint(1000, 9999)}"
        
        # URL de retorno después del pago
        return_url = request.build_absolute_uri(reverse('webpay_return'))
        
        # Crear la transacción en Webpay Plus
        create_response = tx.create(
            buy_order=buy_order,
            session_id=str(venta.id),
            amount=int(venta.total_clp),  # Webpay requiere el monto como entero
            return_url=return_url
        )
        
        # Guardar la orden de compra en la venta para referencia
        venta.buy_order = buy_order
        venta.save()
        
        # Redireccionar al usuario a la página de pago de Webpay
        if hasattr(create_response, 'url') and hasattr(create_response, 'token'):
            return redirect(create_response.url + '?token_ws=' + create_response.token)
        elif isinstance(create_response, dict):
            return redirect(create_response['url'] + '?token_ws=' + create_response['token'])
        else:
            raise Exception("Formato de respuesta no válido de Webpay")
    
    except Venta.DoesNotExist:
        messages.error(request, "No hay ventas pendientes de pago.")
        return redirect("vista_venta")
    except Exception as e:
        messages.error(request, f"Error al procesar el pago: {str(e)}")
        return redirect("vista_venta")

@csrf_exempt
def webpay_return(request):
    # Obtener el token del método GET o POST según corresponda
    token = request.GET.get('token_ws') or request.POST.get('token_ws')
    
    if not token:
        messages.error(request, "No se recibió el token de la transacción")
        return redirect("vista_venta")
    
    try:
        # Configurar las opciones de Webpay
        tx = Transaction(WebpayOptions(commerce_code=COMMERCE_CODE, 
                                     api_key=API_KEY, 
                                     integration_type=IntegrationType.TEST))
        
        # Obtener el estado de la transacción
        commit_response = tx.commit(token=token)
        
        # Verificar si la respuesta es un diccionario
        if isinstance(commit_response, dict):
            status = commit_response.get('status')
            buy_order = commit_response.get('buy_order')
            response_code = commit_response.get('response_code', None)
        else:
            status = commit_response.status
            buy_order = commit_response.buy_order
            response_code = getattr(commit_response, 'response_code', None)
        
        # Buscar la venta por el buy_order
        try:
            venta = Venta.objects.get(buy_order=buy_order)
        except Venta.DoesNotExist:
            messages.error(request, "No se encontró la venta asociada")
            return redirect("vista_venta")
        
        # Verificar si el pago fue exitoso (status AUTHORIZED y response_code 0)
        if status == 'AUTHORIZED' and (response_code == 0 or response_code is None):
            # Verificar que la venta no haya sido procesada anteriormente
            if not venta.pagada:
                # Actualizar el stock según corresponda
                if venta.sucursal == "Casa Matriz":
                    producto_matriz = ProductoCasaMatriz.objects.first()
                    if producto_matriz:
                        if venta.cantidad > producto_matriz.cantidad:
                            messages.error(request, "No hay suficiente stock.")
                            return redirect("vista_venta")
                        producto_matriz.cantidad -= venta.cantidad
                        producto_matriz.save()
                else:
                    try:
                        sucursal = Sucursal.objects.get(id=venta.sucursal_id)
                        if venta.cantidad > sucursal.cantidad:
                            messages.error(request, "No hay suficiente stock.")
                            return redirect("vista_venta")
                        # Usar F() para evitar condiciones de carrera
                        sucursal.cantidad = F('cantidad') - venta.cantidad
                        sucursal.save()
                        # Refrescar el objeto para obtener el valor actualizado
                        sucursal.refresh_from_db()
                    except Sucursal.DoesNotExist:
                        messages.error(request, "Error al procesar el pago: Sucursal no encontrada.")
                        return redirect("vista_venta")
                
                # Marcar la venta como pagada
                venta.pagada = True
                venta.save()
                
                messages.success(request, "¡Pago realizado con éxito! Gracias por tu compra.")
            else:
                messages.info(request, "Esta venta ya fue procesada anteriormente.")
        else:
            messages.error(request, f"El pago no fue autorizado. Estado: {status}")
            
    except Exception as e:
        messages.error(request, f"Error al procesar el pago: {str(e)}")
    
    return redirect("vista_venta")

def inventario(request):
    # Obtener parámetros de filtrado y ordenamiento
    sucursal_filter = request.GET.get('sucursal', 'todas')
    orden = request.GET.get('orden', 'precio_desc')

    # Obtener productos de Casa Matriz
    productos_matriz = ProductoCasaMatriz.objects.all()
    
    # Obtener productos de sucursales
    sucursales = Sucursal.objects.all()
    
    # Preparar lista de todos los productos
    todos_productos = []
    
    # Agregar productos de Casa Matriz
    for producto in productos_matriz:
        todos_productos.append({
            'nombre': producto.nombre,
            'cantidad': producto.cantidad,
            'precio': float(producto.precio),
            'sucursal': 'Casa Matriz'
        })
    
    # Agregar productos de sucursales
    for sucursal in sucursales:
        todos_productos.append({
            'nombre': f"Producto de {sucursal.nombre}",
            'cantidad': sucursal.cantidad,
            'precio': float(sucursal.precio),
            'sucursal': sucursal.nombre
        })
    
    # Filtrar por sucursal si se especifica
    if sucursal_filter != 'todas':
        todos_productos = [p for p in todos_productos if p['sucursal'] == sucursal_filter]
    
    # Ordenar productos según el criterio seleccionado
    if orden == 'precio_asc':
        todos_productos.sort(key=lambda x: x['precio'])
    elif orden == 'precio_desc':
        todos_productos.sort(key=lambda x: x['precio'], reverse=True)
    elif orden == 'stock_asc':
        todos_productos.sort(key=lambda x: x['cantidad'])
    elif orden == 'stock_desc':
        todos_productos.sort(key=lambda x: x['cantidad'], reverse=True)
    
    # Obtener lista de sucursales para el filtro
    lista_sucursales = ['Casa Matriz'] + [s.nombre for s in sucursales]
    
    return render(request, 'ventas/inventario.html', {
        'productos': todos_productos,
        'sucursales': lista_sucursales,
        'sucursal_actual': sucursal_filter,
        'orden_actual': orden
    })

def actualizar_stock(request):
    if request.method == "POST":
        try:
            sucursal = request.POST.get('sucursal')
            nuevo_stock = int(request.POST.get('nuevo_stock'))
            
            if nuevo_stock < 0:
                return JsonResponse({
                    'status': 'error',
                    'message': 'El stock no puede ser negativo'
                })

            if sucursal == 'Casa Matriz':
                producto = ProductoCasaMatriz.objects.first()
                if producto:
                    producto.cantidad = nuevo_stock
                    producto.save()
            else:
                sucursal_obj = Sucursal.objects.get(nombre=sucursal)
                sucursal_obj.cantidad = nuevo_stock
                sucursal_obj.save()

            return JsonResponse({
                'status': 'success',
                'message': f'Stock actualizado correctamente para {sucursal}'
            })
        except (ValueError, Sucursal.DoesNotExist):
            return JsonResponse({
                'status': 'error',
                'message': 'Error al actualizar el stock'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Método no permitido'
    })

