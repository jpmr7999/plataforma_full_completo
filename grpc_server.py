#!/usr/bin/env python3
"""
Servidor gRPC para servicios de productos
Implementa todos los servicios definidos en producto.proto
"""

import grpc
from concurrent import futures
import time
import sys
import os

# Agregar el directorio actual al path para importar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plataforma.settings')
import django
django.setup()

# Importar los modelos y archivos generados
from ventas.models import ProductoCasaMatriz, Sucursal
import producto_pb2
import producto_pb2_grpc
from django.utils import timezone
import math

class ProductoService(producto_pb2_grpc.ProductoServiceServicer):
    """
    Implementación del servicio de productos gRPC
    """
    
    def ListarProductos(self, request, context):
        """Listar productos con paginación y ordenamiento"""
        try:
            # Obtener parámetros
            pagina = request.pagina if request.pagina > 0 else 1
            elementos_por_pagina = min(request.elementos_por_pagina, 100) if request.elementos_por_pagina > 0 else 10
            ordenar_por = request.ordenar_por
            orden = request.orden
            
            # Calcular offset
            offset = (pagina - 1) * elementos_por_pagina
            
            # Obtener productos de Casa Matriz
            productos_matriz = ProductoCasaMatriz.objects.all()
            
            # Obtener productos de Sucursales
            sucursales = Sucursal.objects.all()
            
            # Convertir a formato gRPC
            productos_grpc = []
            
            for producto in productos_matriz:
                productos_grpc.append(producto_pb2.Producto(
                    id=producto.id,
                    nombre=producto.nombre,
                    cantidad=producto.cantidad,
                    precio=float(producto.precio),
                    sucursal="Casa Matriz",
                    fecha_creacion=producto.id,  # Usar ID como fecha por simplicidad
                    activo=True
                ))
            
            for sucursal in sucursales:
                productos_grpc.append(producto_pb2.Producto(
                    id=sucursal.id,
                    nombre=f"Producto de {sucursal.nombre}",
                    cantidad=sucursal.cantidad,
                    precio=float(sucursal.precio),
                    sucursal=sucursal.nombre,
                    fecha_creacion=sucursal.id,
                    activo=True
                ))
            
            # Aplicar ordenamiento
            if ordenar_por == "nombre":
                productos_grpc.sort(key=lambda x: x.nombre, reverse=(orden == "desc"))
            elif ordenar_por == "precio":
                productos_grpc.sort(key=lambda x: x.precio, reverse=(orden == "desc"))
            elif ordenar_por == "cantidad":
                productos_grpc.sort(key=lambda x: x.cantidad, reverse=(orden == "desc"))
            
            # Aplicar paginación
            total_productos = len(productos_grpc)
            productos_paginados = productos_grpc[offset:offset + elementos_por_pagina]
            total_paginas = math.ceil(total_productos / elementos_por_pagina)
            
            return producto_pb2.ListarProductosResponse(
                productos=productos_paginados,
                total_productos=total_productos,
                pagina_actual=pagina,
                total_paginas=total_paginas,
                mensaje="Productos listados exitosamente",
                exito=True
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Error al listar productos: {str(e)}')
            return producto_pb2.ListarProductosResponse(
                productos=[],
                total_productos=0,
                pagina_actual=1,
                total_paginas=0,
                mensaje=f"Error: {str(e)}",
                exito=False
            )
    
    def CrearProducto(self, request, context):
        """Crear un nuevo producto"""
        try:
            nombre = request.nombre
            cantidad = request.cantidad
            precio = request.precio
            tipo_sucursal = request.tipo_sucursal
            
            # Validaciones
            if cantidad < 0 or precio < 0:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details('Cantidad y precio deben ser positivos')
                return producto_pb2.CrearProductoResponse(
                    producto=None,
                    mensaje="Cantidad y precio deben ser positivos",
                    exito=False
                )
            
            if tipo_sucursal == "casa_matriz":
                # Crear producto en Casa Matriz
                producto = ProductoCasaMatriz.objects.create(
                    nombre=nombre,
                    cantidad=cantidad,
                    precio=precio
                )
                sucursal_nombre = "Casa Matriz"
            elif tipo_sucursal == "sucursal":
                # Crear producto en Sucursal
                nombre_sucursal = request.nombre_sucursal
                if not nombre_sucursal:
                    context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                    context.set_details('Nombre de sucursal requerido')
                    return producto_pb2.CrearProductoResponse(
                        producto=None,
                        mensaje="Nombre de sucursal requerido",
                        exito=False
                    )
                
                producto = Sucursal.objects.create(
                    nombre=nombre_sucursal,
                    cantidad=cantidad,
                    precio=precio
                )
                sucursal_nombre = nombre_sucursal
            else:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details('Tipo de sucursal inválido')
                return producto_pb2.CrearProductoResponse(
                    producto=None,
                    mensaje="Tipo de sucursal inválido",
                    exito=False
                )
            
            # Crear respuesta gRPC
            producto_grpc = producto_pb2.Producto(
                id=producto.id,
                nombre=nombre if tipo_sucursal == "casa_matriz" else f"Producto de {sucursal_nombre}",
                cantidad=producto.cantidad,
                precio=float(producto.precio),
                sucursal=sucursal_nombre,
                fecha_creacion=producto.id,
                activo=True
            )
            
            return producto_pb2.CrearProductoResponse(
                producto=producto_grpc,
                mensaje=f"Producto creado exitosamente en {sucursal_nombre}",
                exito=True
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Error al crear producto: {str(e)}')
            return producto_pb2.CrearProductoResponse(
                producto=None,
                mensaje=f"Error: {str(e)}",
                exito=False
            )
    
    def ObtenerProducto(self, request, context):
        """Obtener un producto por ID"""
        try:
            producto_id = request.id
            
            # Buscar en Casa Matriz
            try:
                producto = ProductoCasaMatriz.objects.get(id=producto_id)
                sucursal_nombre = "Casa Matriz"
                nombre_producto = producto.nombre
            except ProductoCasaMatriz.DoesNotExist:
                # Buscar en Sucursales
                try:
                    producto = Sucursal.objects.get(id=producto_id)
                    sucursal_nombre = producto.nombre
                    nombre_producto = f"Producto de {producto.nombre}"
                except Sucursal.DoesNotExist:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details('Producto no encontrado')
                    return producto_pb2.ObtenerProductoResponse(
                        producto=None,
                        mensaje="Producto no encontrado",
                        exito=False
                    )
            
            producto_grpc = producto_pb2.Producto(
                id=producto.id,
                nombre=nombre_producto,
                cantidad=producto.cantidad,
                precio=float(producto.precio),
                sucursal=sucursal_nombre,
                fecha_creacion=producto.id,
                activo=True
            )
            
            return producto_pb2.ObtenerProductoResponse(
                producto=producto_grpc,
                mensaje="Producto encontrado",
                exito=True
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Error al obtener producto: {str(e)}')
            return producto_pb2.ObtenerProductoResponse(
                producto=None,
                mensaje=f"Error: {str(e)}",
                exito=False
            )
    
    def ActualizarProducto(self, request, context):
        """Actualizar un producto existente"""
        try:
            producto_id = request.id
            nombre = request.nombre
            cantidad = request.cantidad
            precio = request.precio
            sucursal = request.sucursal
            
            # Validaciones
            if cantidad < 0 or precio < 0:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details('Cantidad y precio deben ser positivos')
                return producto_pb2.ActualizarProductoResponse(
                    producto=None,
                    mensaje="Cantidad y precio deben ser positivos",
                    exito=False
                )
            
            # Buscar y actualizar producto
            if sucursal == "Casa Matriz":
                try:
                    producto = ProductoCasaMatriz.objects.get(id=producto_id)
                    producto.nombre = nombre
                    producto.cantidad = cantidad
                    producto.precio = precio
                    producto.save()
                except ProductoCasaMatriz.DoesNotExist:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details('Producto no encontrado')
                    return producto_pb2.ActualizarProductoResponse(
                        producto=None,
                        mensaje="Producto no encontrado",
                        exito=False
                    )
            else:
                try:
                    producto = Sucursal.objects.get(id=producto_id)
                    producto.nombre = sucursal
                    producto.cantidad = cantidad
                    producto.precio = precio
                    producto.save()
                except Sucursal.DoesNotExist:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details('Producto no encontrado')
                    return producto_pb2.ActualizarProductoResponse(
                        producto=None,
                        mensaje="Producto no encontrado",
                        exito=False
                    )
            
            producto_grpc = producto_pb2.Producto(
                id=producto.id,
                nombre=nombre if sucursal == "Casa Matriz" else f"Producto de {sucursal}",
                cantidad=producto.cantidad,
                precio=float(producto.precio),
                sucursal=sucursal,
                fecha_creacion=producto.id,
                activo=True
            )
            
            return producto_pb2.ActualizarProductoResponse(
                producto=producto_grpc,
                mensaje="Producto actualizado exitosamente",
                exito=True
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Error al actualizar producto: {str(e)}')
            return producto_pb2.ActualizarProductoResponse(
                producto=None,
                mensaje=f"Error: {str(e)}",
                exito=False
            )
    
    def EliminarProducto(self, request, context):
        """Eliminar un producto (soft delete)"""
        try:
            producto_id = request.id
            
            # Buscar y eliminar de Casa Matriz
            try:
                producto = ProductoCasaMatriz.objects.get(id=producto_id)
                producto.delete()
            except ProductoCasaMatriz.DoesNotExist:
                # Buscar y eliminar de Sucursales
                try:
                    producto = Sucursal.objects.get(id=producto_id)
                    producto.delete()
                except Sucursal.DoesNotExist:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details('Producto no encontrado')
                    return producto_pb2.EliminarProductoResponse(
                        mensaje="Producto no encontrado",
                        exito=False
                    )
            
            return producto_pb2.EliminarProductoResponse(
                mensaje="Producto eliminado exitosamente",
                exito=True
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Error al eliminar producto: {str(e)}')
            return producto_pb2.EliminarProductoResponse(
                mensaje=f"Error: {str(e)}",
                exito=False
            )
    
    def BuscarProductos(self, request, context):
        """Buscar productos por nombre"""
        try:
            termino_busqueda = request.termino_busqueda.lower()
            pagina = request.pagina if request.pagina > 0 else 1
            elementos_por_pagina = min(request.elementos_por_pagina, 100) if request.elementos_por_pagina > 0 else 10
            offset = (pagina - 1) * elementos_por_pagina
            
            productos_encontrados = []
            
            # Buscar en Casa Matriz
            productos_matriz = ProductoCasaMatriz.objects.filter(nombre__icontains=termino_busqueda)
            for producto in productos_matriz:
                productos_encontrados.append(producto_pb2.Producto(
                    id=producto.id,
                    nombre=producto.nombre,
                    cantidad=producto.cantidad,
                    precio=float(producto.precio),
                    sucursal="Casa Matriz",
                    fecha_creacion=producto.id,
                    activo=True
                ))
            
            # Buscar en Sucursales
            sucursales = Sucursal.objects.filter(nombre__icontains=termino_busqueda)
            for sucursal in sucursales:
                productos_encontrados.append(producto_pb2.Producto(
                    id=sucursal.id,
                    nombre=f"Producto de {sucursal.nombre}",
                    cantidad=sucursal.cantidad,
                    precio=float(sucursal.precio),
                    sucursal=sucursal.nombre,
                    fecha_creacion=sucursal.id,
                    activo=True
                ))
            
            # Aplicar paginación
            total_encontrados = len(productos_encontrados)
            productos_paginados = productos_encontrados[offset:offset + elementos_por_pagina]
            
            return producto_pb2.BuscarProductosResponse(
                productos=productos_paginados,
                total_encontrados=total_encontrados,
                mensaje=f"Se encontraron {total_encontrados} productos",
                exito=True
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Error al buscar productos: {str(e)}')
            return producto_pb2.BuscarProductosResponse(
                productos=[],
                total_encontrados=0,
                mensaje=f"Error: {str(e)}",
                exito=False
            )
    
    def ProductosPorSucursal(self, request, context):
        """Obtener productos de una sucursal específica"""
        try:
            sucursal_nombre = request.sucursal
            pagina = request.pagina if request.pagina > 0 else 1
            elementos_por_pagina = min(request.elementos_por_pagina, 100) if request.elementos_por_pagina > 0 else 10
            offset = (pagina - 1) * elementos_por_pagina
            
            productos_sucursal = []
            
            if sucursal_nombre == "Casa Matriz":
                productos = ProductoCasaMatriz.objects.all()
                for producto in productos:
                    productos_sucursal.append(producto_pb2.Producto(
                        id=producto.id,
                        nombre=producto.nombre,
                        cantidad=producto.cantidad,
                        precio=float(producto.precio),
                        sucursal="Casa Matriz",
                        fecha_creacion=producto.id,
                        activo=True
                    ))
            else:
                sucursales = Sucursal.objects.filter(nombre=sucursal_nombre)
                for sucursal in sucursales:
                    productos_sucursal.append(producto_pb2.Producto(
                        id=sucursal.id,
                        nombre=f"Producto de {sucursal.nombre}",
                        cantidad=sucursal.cantidad,
                        precio=float(sucursal.precio),
                        sucursal=sucursal.nombre,
                        fecha_creacion=sucursal.id,
                        activo=True
                    ))
            
            # Aplicar paginación
            total_productos = len(productos_sucursal)
            productos_paginados = productos_sucursal[offset:offset + elementos_por_pagina]
            
            return producto_pb2.ProductosPorSucursalResponse(
                productos=productos_paginados,
                total_productos=total_productos,
                mensaje=f"Productos de {sucursal_nombre}",
                exito=True
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Error al obtener productos por sucursal: {str(e)}')
            return producto_pb2.ProductosPorSucursalResponse(
                productos=[],
                total_productos=0,
                mensaje=f"Error: {str(e)}",
                exito=False
            )
    
    def ActualizarStock(self, request, context):
        """Actualizar el stock de un producto"""
        try:
            producto_id = request.id
            nueva_cantidad = request.nueva_cantidad
            
            if nueva_cantidad < 0:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details('La cantidad no puede ser negativa')
                return producto_pb2.ActualizarStockResponse(
                    producto=None,
                    mensaje="La cantidad no puede ser negativa",
                    exito=False
                )
            
            # Buscar y actualizar en Casa Matriz
            try:
                producto = ProductoCasaMatriz.objects.get(id=producto_id)
                producto.cantidad = nueva_cantidad
                producto.save()
                sucursal_nombre = "Casa Matriz"
                nombre_producto = producto.nombre
            except ProductoCasaMatriz.DoesNotExist:
                # Buscar y actualizar en Sucursales
                try:
                    producto = Sucursal.objects.get(id=producto_id)
                    producto.cantidad = nueva_cantidad
                    producto.save()
                    sucursal_nombre = producto.nombre
                    nombre_producto = f"Producto de {producto.nombre}"
                except Sucursal.DoesNotExist:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details('Producto no encontrado')
                    return producto_pb2.ActualizarStockResponse(
                        producto=None,
                        mensaje="Producto no encontrado",
                        exito=False
                    )
            
            producto_grpc = producto_pb2.Producto(
                id=producto.id,
                nombre=nombre_producto,
                cantidad=producto.cantidad,
                precio=float(producto.precio),
                sucursal=sucursal_nombre,
                fecha_creacion=producto.id,
                activo=True
            )
            
            return producto_pb2.ActualizarStockResponse(
                producto=producto_grpc,
                mensaje=f"Stock actualizado a {nueva_cantidad} unidades",
                exito=True
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Error al actualizar stock: {str(e)}')
            return producto_pb2.ActualizarStockResponse(
                producto=None,
                mensaje=f"Error: {str(e)}",
                exito=False
            )

def serve():
    """Iniciar el servidor gRPC"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    producto_pb2_grpc.add_ProductoServiceServicer_to_server(ProductoService(), server)
    
    # Puerto del servidor gRPC
    listen_addr = '[::]:50051'
    server.add_insecure_port(listen_addr)
    
    print(f"🚀 Servidor gRPC iniciado en {listen_addr}")
    print("📋 Servicios disponibles:")
    print("   - ListarProductos")
    print("   - CrearProducto")
    print("   - ObtenerProducto")
    print("   - ActualizarProducto")
    print("   - EliminarProducto")
    print("   - BuscarProductos")
    print("   - ProductosPorSucursal")
    print("   - ActualizarStock")
    print("\n💡 Para probar el cliente gRPC, ejecuta: python grpc_client.py")
    
    server.start()
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\n🛑 Servidor gRPC detenido")
        server.stop(0)

if __name__ == '__main__':
    serve() 