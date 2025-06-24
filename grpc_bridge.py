#!/usr/bin/env python3
"""
Bridge gRPC para conectar servicios gRPC con Django
Permite que las vistas de Django usen servicios gRPC internamente
"""

import grpc
import producto_pb2
import producto_pb2_grpc
import os
import sys
import django
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plataforma.settings')
django.setup()

class GRPCBridge:
    """
    Bridge para conectar Django con servicios gRPC
    """
    
    def __init__(self, host='localhost', port=50051):
        self.host = host
        self.port = port
        self.channel = None
        self.stub = None
    
    def connect(self):
        """Conectar al servidor gRPC"""
        try:
            self.channel = grpc.insecure_channel(f'{self.host}:{self.port}')
            self.stub = producto_pb2_grpc.ProductoServiceStub(self.channel)
            return True
        except Exception as e:
            print(f"Error conectando al servidor gRPC: {e}")
            return False
    
    def disconnect(self):
        """Desconectar del servidor gRPC"""
        if self.channel:
            self.channel.close()
    
    def listar_productos(self, pagina=1, elementos_por_pagina=10, ordenar_por="nombre", orden="asc"):
        """Listar productos usando gRPC"""
        try:
            if not self.stub:
                if not self.connect():
                    return None
            
            response = self.stub.ListarProductos(producto_pb2.ListarProductosRequest(
                pagina=pagina,
                elementos_por_pagina=elementos_por_pagina,
                ordenar_por=ordenar_por,
                orden=orden
            ))
            
            return {
                'productos': response.productos,
                'total_productos': response.total_productos,
                'pagina_actual': response.pagina_actual,
                'total_paginas': response.total_paginas,
                'mensaje': response.mensaje,
                'exito': response.exito
            }
            
        except grpc.RpcError as e:
            print(f"Error gRPC: {e.code()}: {e.details()}")
            return None
        except Exception as e:
            print(f"Error inesperado: {e}")
            return None
    
    def crear_producto(self, nombre, cantidad, precio, tipo_sucursal="casa_matriz", nombre_sucursal=""):
        """Crear producto usando gRPC"""
        try:
            if not self.stub:
                if not self.connect():
                    return None
            
            request = producto_pb2.CrearProductoRequest(
                nombre=nombre,
                cantidad=cantidad,
                precio=precio,
                tipo_sucursal=tipo_sucursal
            )
            
            if tipo_sucursal == "sucursal":
                request.nombre_sucursal = nombre_sucursal
            
            response = self.stub.CrearProducto(request)
            
            return {
                'producto': response.producto,
                'mensaje': response.mensaje,
                'exito': response.exito
            }
            
        except grpc.RpcError as e:
            print(f"Error gRPC: {e.code()}: {e.details()}")
            return None
        except Exception as e:
            print(f"Error inesperado: {e}")
            return None
    
    def obtener_producto(self, producto_id):
        """Obtener producto usando gRPC"""
        try:
            if not self.stub:
                if not self.connect():
                    return None
            
            response = self.stub.ObtenerProducto(producto_pb2.ObtenerProductoRequest(id=producto_id))
            
            return {
                'producto': response.producto,
                'mensaje': response.mensaje,
                'exito': response.exito
            }
            
        except grpc.RpcError as e:
            print(f"Error gRPC: {e.code()}: {e.details()}")
            return None
        except Exception as e:
            print(f"Error inesperado: {e}")
            return None
    
    def actualizar_producto(self, producto_id, nombre, cantidad, precio, sucursal):
        """Actualizar producto usando gRPC"""
        try:
            if not self.stub:
                if not self.connect():
                    return None
            
            response = self.stub.ActualizarProducto(producto_pb2.ActualizarProductoRequest(
                id=producto_id,
                nombre=nombre,
                cantidad=cantidad,
                precio=precio,
                sucursal=sucursal
            ))
            
            return {
                'producto': response.producto,
                'mensaje': response.mensaje,
                'exito': response.exito
            }
            
        except grpc.RpcError as e:
            print(f"Error gRPC: {e.code()}: {e.details()}")
            return None
        except Exception as e:
            print(f"Error inesperado: {e}")
            return None
    
    def eliminar_producto(self, producto_id):
        """Eliminar producto usando gRPC"""
        try:
            if not self.stub:
                if not self.connect():
                    return None
            
            response = self.stub.EliminarProducto(producto_pb2.EliminarProductoRequest(id=producto_id))
            
            return {
                'mensaje': response.mensaje,
                'exito': response.exito
            }
            
        except grpc.RpcError as e:
            print(f"Error gRPC: {e.code()}: {e.details()}")
            return None
        except Exception as e:
            print(f"Error inesperado: {e}")
            return None
    
    def buscar_productos(self, termino_busqueda, pagina=1, elementos_por_pagina=10):
        """Buscar productos usando gRPC"""
        try:
            if not self.stub:
                if not self.connect():
                    return None
            
            response = self.stub.BuscarProductos(producto_pb2.BuscarProductosRequest(
                termino_busqueda=termino_busqueda,
                pagina=pagina,
                elementos_por_pagina=elementos_por_pagina
            ))
            
            return {
                'productos': response.productos,
                'total_encontrados': response.total_encontrados,
                'mensaje': response.mensaje,
                'exito': response.exito
            }
            
        except grpc.RpcError as e:
            print(f"Error gRPC: {e.code()}: {e.details()}")
            return None
        except Exception as e:
            print(f"Error inesperado: {e}")
            return None
    
    def productos_por_sucursal(self, sucursal, pagina=1, elementos_por_pagina=10):
        """Obtener productos por sucursal usando gRPC"""
        try:
            if not self.stub:
                if not self.connect():
                    return None
            
            response = self.stub.ProductosPorSucursal(producto_pb2.ProductosPorSucursalRequest(
                sucursal=sucursal,
                pagina=pagina,
                elementos_por_pagina=elementos_por_pagina
            ))
            
            return {
                'productos': response.productos,
                'total_productos': response.total_productos,
                'mensaje': response.mensaje,
                'exito': response.exito
            }
            
        except grpc.RpcError as e:
            print(f"Error gRPC: {e.code()}: {e.details()}")
            return None
        except Exception as e:
            print(f"Error inesperado: {e}")
            return None
    
    def actualizar_stock(self, producto_id, nueva_cantidad):
        """Actualizar stock usando gRPC"""
        try:
            if not self.stub:
                if not self.connect():
                    return None
            
            response = self.stub.ActualizarStock(producto_pb2.ActualizarStockRequest(
                id=producto_id,
                nueva_cantidad=nueva_cantidad
            ))
            
            return {
                'producto': response.producto,
                'mensaje': response.mensaje,
                'exito': response.exito
            }
            
        except grpc.RpcError as e:
            print(f"Error gRPC: {e.code()}: {e.details()}")
            return None
        except Exception as e:
            print(f"Error inesperado: {e}")
            return None

# Instancia global del bridge
grpc_bridge = GRPCBridge()

def get_grpc_bridge():
    """Obtener instancia del bridge gRPC"""
    return grpc_bridge

# Ejemplo de uso en vistas de Django
def ejemplo_uso_en_vista():
    """
    Ejemplo de cómo usar el bridge en una vista de Django
    """
    bridge = get_grpc_bridge()
    
    # Listar productos
    productos = bridge.listar_productos(pagina=1, elementos_por_pagina=10)
    if productos and productos['exito']:
        print(f"Productos obtenidos: {productos['total_productos']}")
        for producto in productos['productos']:
            print(f"- {producto.nombre} ({producto.sucursal})")
    
    # Crear producto
    nuevo_producto = bridge.crear_producto(
        nombre="Producto Test",
        cantidad=10,
        precio=50000.0,
        tipo_sucursal="casa_matriz"
    )
    if nuevo_producto and nuevo_producto['exito']:
        print(f"Producto creado: {nuevo_producto['mensaje']}")
    
    # Buscar productos
    busqueda = bridge.buscar_productos("Test", pagina=1, elementos_por_pagina=5)
    if busqueda and busqueda['exito']:
        print(f"Búsqueda exitosa: {busqueda['total_encontrados']} productos encontrados")

if __name__ == '__main__':
    # Ejemplo de uso
    ejemplo_uso_en_vista() 