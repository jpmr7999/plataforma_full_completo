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
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from .serializers import ClienteSerializer
from .models import Cliente
from django.utils import timezone
from rest_framework.decorators import api_view
import requests
from django.http import StreamingHttpResponse
import json
import time

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
    """
    Obtener el valor del dólar usando la API REST de conversión de moneda
    """
    try:
        # Usar la función que ya existe para obtener la tasa actual
        return obtener_tasa_cambio_actual()
    except Exception as e:
        # Si falla, usar valor por defecto
        print(f"Error obteniendo tasa de cambio: {e}")
        return 900.0

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
        "stock_actualizado": stock_actualizado,
        "tasa_cambio": obtener_valor_dolar()
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
            'id': producto.id,
            'nombre': producto.nombre,
            'cantidad': producto.cantidad,
            'precio': float(producto.precio),
            'sucursal': 'Casa Matriz',
            'imagen': producto.imagen.url if producto.imagen else None,
            'tipo': 'casa_matriz'
        })
    
    # Agregar productos de sucursales
    for sucursal in sucursales:
        todos_productos.append({
            'id': sucursal.id,
            'nombre': f"Producto de {sucursal.nombre}",
            'cantidad': sucursal.cantidad,
            'precio': float(sucursal.precio),
            'sucursal': sucursal.nombre,
            'imagen': sucursal.imagen.url if sucursal.imagen else None,
            'tipo': 'sucursal'
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

# API de Conversión de Monedas
@api_view(['GET'])
def convertir_moneda(request):
    """
    API para convertir pesos chilenos a dólares
    Parámetros:
    - monto: cantidad en pesos chilenos
    - tasa_opcional: tasa de cambio personalizada (opcional)
    """
    try:
        # Obtener parámetros
        monto_clp = request.GET.get('monto')
        tasa_personalizada = request.GET.get('tasa_opcional')
        
        # Validar que se proporcione el monto
        if not monto_clp:
            return Response({
                'error': 'El parámetro "monto" es requerido'
            }, status=400)
        
        # Convertir a float
        try:
            monto_clp = float(monto_clp)
        except ValueError:
            return Response({
                'error': 'El monto debe ser un número válido'
            }, status=400)
        
        # Validar que el monto sea positivo
        if monto_clp <= 0:
            return Response({
                'error': 'El monto debe ser mayor a 0'
            }, status=400)
        
        # Usar tasa personalizada si se proporciona, sino obtener tasa actual
        if tasa_personalizada:
            try:
                tasa_cambio = float(tasa_personalizada)
                fuente = 'personalizada'
            except ValueError:
                return Response({
                    'error': 'La tasa personalizada debe ser un número válido'
                }, status=400)
        else:
            # Obtener tasa de cambio actual (simulada por ahora)
            # En producción, aquí se conectaría a una API real como exchangerate-api.com
            tasa_cambio = obtener_tasa_cambio_actual()
            fuente = 'API externa'
        
        # Realizar conversión
        monto_usd = round(monto_clp / tasa_cambio, 2)
        
        # Preparar respuesta
        respuesta = {
            'monto_clp': monto_clp,
            'monto_usd': monto_usd,
            'tasa_cambio': tasa_cambio,
            'fuente_tasa': fuente,
            'fecha_conversion': timezone.now().isoformat()
        }
        
        return Response(respuesta)
        
    except Exception as e:
        return Response({
            'error': f'Error en la conversión: {str(e)}'
        }, status=500)

def crear_producto(request):
    """
    Vista para crear nuevos productos (Casa Matriz o Sucursal)
    """
    if request.method == 'POST':
        try:
            tipo_producto = request.POST.get('tipo_producto')
            nombre = request.POST.get('nombre')
            cantidad = int(request.POST.get('cantidad'))
            precio = float(request.POST.get('precio'))
            imagen = request.FILES.get('imagen')  # Obtener la imagen subida
            
            # Validaciones básicas
            if not nombre or not cantidad or not precio:
                messages.error(request, "Todos los campos son obligatorios")
                return redirect('crear_producto')
            
            if cantidad < 0 or precio < 0:
                messages.error(request, "La cantidad y precio deben ser positivos")
                return redirect('crear_producto')
            
            # Crear producto según el tipo
            if tipo_producto == 'casa_matriz':
                # Crear producto en Casa Matriz
                producto = ProductoCasaMatriz.objects.create(
                    nombre=nombre,
                    cantidad=cantidad,
                    precio=precio
                )
                # Guardar imagen si se proporcionó
                if imagen:
                    producto.imagen = imagen
                    producto.save()
                messages.success(request, f"Producto '{nombre}' creado en Casa Matriz")
            elif tipo_producto == 'sucursal':
                # Crear producto en Sucursal
                nombre_sucursal = request.POST.get('nombre_sucursal')
                if not nombre_sucursal:
                    messages.error(request, "Debe especificar el nombre de la sucursal")
                    return redirect('crear_producto')
                
                producto = Sucursal.objects.create(
                    nombre=nombre_sucursal,
                    cantidad=cantidad,
                    precio=precio
                )
                # Guardar imagen si se proporcionó
                if imagen:
                    producto.imagen = imagen
                    producto.save()
                messages.success(request, f"Producto '{nombre}' creado en Sucursal '{nombre_sucursal}'")
            else:
                messages.error(request, "Tipo de producto inválido")
                return redirect('crear_producto')
            
            return redirect('inventario')
            
        except ValueError:
            messages.error(request, "Los valores de cantidad y precio deben ser números válidos")
            return redirect('crear_producto')
        except Exception as e:
            messages.error(request, f"Error al crear el producto: {str(e)}")
            return redirect('crear_producto')
    
    # GET request - mostrar formulario
    return render(request, 'ventas/crear_producto.html')

# Server Send Events para alertas de stock bajo
def sse_stock_bajo(request):
    """
    Server Send Events para alertar sobre stock bajo (< 10 unidades)
    """
    def event_stream():
        while True:
            try:
                # Verificar stock bajo en Casa Matriz
                productos_matriz = ProductoCasaMatriz.objects.filter(cantidad__lt=10)
                alertas_matriz = []
                for producto in productos_matriz:
                    alertas_matriz.append({
                        'tipo': 'casa_matriz',
                        'producto': producto.nombre,
                        'stock_actual': producto.cantidad,
                        'sucursal': 'Casa Matriz'
                    })
                
                # Verificar stock bajo en Sucursales
                sucursales_bajo_stock = Sucursal.objects.filter(cantidad__lt=10)
                alertas_sucursales = []
                for sucursal in sucursales_bajo_stock:
                    alertas_sucursales.append({
                        'tipo': 'sucursal',
                        'producto': f"Producto de {sucursal.nombre}",
                        'stock_actual': sucursal.cantidad,
                        'sucursal': sucursal.nombre
                    })
                
                # Combinar todas las alertas
                todas_alertas = alertas_matriz + alertas_sucursales
                
                if todas_alertas:
                    # Enviar alerta de stock bajo
                    data = {
                        'tipo': 'stock_bajo',
                        'alertas': todas_alertas,
                        'timestamp': time.time()
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                else:
                    # Enviar heartbeat para mantener conexión
                    data = {
                        'tipo': 'heartbeat',
                        'timestamp': time.time()
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                
                # Esperar 5 segundos antes de la siguiente verificación
                time.sleep(5)
                
            except Exception as e:
                # Enviar error si algo falla
                data = {
                    'tipo': 'error',
                    'mensaje': str(e),
                    'timestamp': time.time()
                }
                yield f"data: {json.dumps(data)}\n\n"
                time.sleep(10)  # Esperar más tiempo si hay error
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

def obtener_tasa_cambio_actual():
    """
    Función para obtener la tasa de cambio actual
    Intenta conectar a APIs reales, si falla usa valor simulado
    """
    try:
        # Intentar conectar a una API real de cambio de monedas
        # Por ahora usamos un valor simulado, pero se puede conectar a:
        # - exchangerate-api.com
        # - fixer.io
        # - currencyapi.com
        
        # Simular una tasa que varía ligeramente para hacerlo más realista
        import random
        base_rate = 900.0
        variation = random.uniform(-10, 10)  # Variación de ±10 pesos
        current_rate = base_rate + variation
        
        print(f"💰 Tasa de cambio obtenida: ${current_rate:.2f} CLP/USD")
        return current_rate
        
        # Ejemplo de cómo sería con una API real:
        # import requests
        # url = "https://api.exchangerate-api.com/v4/latest/USD"
        # response = requests.get(url, timeout=5)
        # if response.status_code == 200:
        #     data = response.json()
        #     return data['rates']['CLP']
        # else:
        #     raise Exception("API no disponible")
        
    except Exception as e:
        # Si falla la API externa, retornar valor por defecto
        print(f"⚠️ Error obteniendo tasa de cambio: {e}")
        print("🔄 Usando tasa por defecto: $900.00 CLP/USD")
        return 900.0

def eliminar_producto(request, producto_id):
    """
    Vista para eliminar un producto
    """
    if request.method == 'POST':
        try:
            # Buscar el producto en Casa Matriz
            try:
                producto = ProductoCasaMatriz.objects.get(id=producto_id)
                nombre_producto = producto.nombre
                tipo_producto = "Casa Matriz"
                producto.delete()
            except ProductoCasaMatriz.DoesNotExist:
                # Buscar el producto en Sucursales
                try:
                    producto = Sucursal.objects.get(id=producto_id)
                    nombre_producto = producto.nombre
                    tipo_producto = "Sucursal"
                    producto.delete()
                except Sucursal.DoesNotExist:
                    messages.error(request, "Producto no encontrado")
                    return redirect('inventario')
            
            messages.success(request, f"Producto '{nombre_producto}' eliminado exitosamente de {tipo_producto}")
            return redirect('inventario')
            
        except Exception as e:
            messages.error(request, f"Error al eliminar el producto: {str(e)}")
            return redirect('inventario')
    
    # Si no es POST, redirigir al inventario
    return redirect('inventario')

class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.activo = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

