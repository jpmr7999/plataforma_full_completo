#!/usr/bin/env python3
"""
Cliente gRPC para probar servicios de productos
"""

import grpc
import producto_pb2
import producto_pb2_grpc
import time

def run():
    """Ejecutar pruebas del cliente gRPC"""
    
    # Conectar al servidor gRPC
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = producto_pb2_grpc.ProductoServiceStub(channel)
        
        print("🚀 Cliente gRPC conectado al servidor")
        print("=" * 50)
        
        try:
            # 1. Listar productos
            print("\n📋 1. Listando productos...")
            response = stub.ListarProductos(producto_pb2.ListarProductosRequest(
                pagina=1,
                elementos_por_pagina=10,
                ordenar_por="nombre",
                orden="asc"
            ))
            
            if response.exito:
                print(f"✅ {response.mensaje}")
                print(f"📊 Total productos: {response.total_productos}")
                print(f"📄 Página {response.pagina_actual} de {response.total_paginas}")
                
                for producto in response.productos:
                    print(f"   - {producto.nombre} ({producto.sucursal}) - {producto.cantidad} uds - ${producto.precio}")
            else:
                print(f"❌ Error: {response.mensaje}")
            
            # 2. Crear producto en Casa Matriz
            print("\n➕ 2. Creando producto en Casa Matriz...")
            response = stub.CrearProducto(producto_pb2.CrearProductoRequest(
                nombre="Laptop Gaming Pro",
                cantidad=15,
                precio=899990.0,
                tipo_sucursal="casa_matriz"
            ))
            
            if response.exito:
                print(f"✅ {response.mensaje}")
                producto_creado = response.producto
                print(f"   ID: {producto_creado.id}")
                print(f"   Nombre: {producto_creado.nombre}")
                print(f"   Sucursal: {producto_creado.sucursal}")
                producto_id = producto_creado.id
            else:
                print(f"❌ Error: {response.mensaje}")
                producto_id = 1  # Usar ID por defecto para pruebas
            
            # 3. Crear producto en Sucursal
            print("\n➕ 3. Creando producto en Sucursal...")
            response = stub.CrearProducto(producto_pb2.CrearProductoRequest(
                nombre="Sucursal Centro",
                cantidad=8,
                precio=750000.0,
                tipo_sucursal="sucursal",
                nombre_sucursal="Sucursal Centro"
            ))
            
            if response.exito:
                print(f"✅ {response.mensaje}")
                producto_creado = response.producto
                print(f"   ID: {producto_creado.id}")
                print(f"   Nombre: {producto_creado.nombre}")
                print(f"   Sucursal: {producto_creado.sucursal}")
                sucursal_id = producto_creado.id
            else:
                print(f"❌ Error: {response.mensaje}")
                sucursal_id = 2  # Usar ID por defecto para pruebas
            
            # 4. Obtener producto específico
            print(f"\n🔍 4. Obteniendo producto ID {producto_id}...")
            response = stub.ObtenerProducto(producto_pb2.ObtenerProductoRequest(id=producto_id))
            
            if response.exito:
                print(f"✅ {response.mensaje}")
                producto = response.producto
                print(f"   Nombre: {producto.nombre}")
                print(f"   Cantidad: {producto.cantidad}")
                print(f"   Precio: ${producto.precio}")
                print(f"   Sucursal: {producto.sucursal}")
            else:
                print(f"❌ Error: {response.mensaje}")
            
            # 5. Buscar productos
            print("\n🔎 5. Buscando productos con 'Laptop'...")
            response = stub.BuscarProductos(producto_pb2.BuscarProductosRequest(
                termino_busqueda="Laptop",
                pagina=1,
                elementos_por_pagina=5
            ))
            
            if response.exito:
                print(f"✅ {response.mensaje}")
                print(f"📊 Total encontrados: {response.total_encontrados}")
                
                for producto in response.productos:
                    print(f"   - {producto.nombre} ({producto.sucursal}) - {producto.cantidad} uds")
            else:
                print(f"❌ Error: {response.mensaje}")
            
            # 6. Productos por sucursal
            print("\n🏢 6. Productos de Casa Matriz...")
            response = stub.ProductosPorSucursal(producto_pb2.ProductosPorSucursalRequest(
                sucursal="Casa Matriz",
                pagina=1,
                elementos_por_pagina=10
            ))
            
            if response.exito:
                print(f"✅ {response.mensaje}")
                print(f"📊 Total productos: {response.total_productos}")
                
                for producto in response.productos:
                    print(f"   - {producto.nombre} - {producto.cantidad} uds - ${producto.precio}")
            else:
                print(f"❌ Error: {response.mensaje}")
            
            # 7. Actualizar stock
            print(f"\n📦 7. Actualizando stock del producto ID {producto_id}...")
            response = stub.ActualizarStock(producto_pb2.ActualizarStockRequest(
                id=producto_id,
                nueva_cantidad=25
            ))
            
            if response.exito:
                print(f"✅ {response.mensaje}")
                producto = response.producto
                print(f"   Nuevo stock: {producto.cantidad} unidades")
            else:
                print(f"❌ Error: {response.mensaje}")
            
            # 8. Actualizar producto
            print(f"\n✏️ 8. Actualizando producto ID {producto_id}...")
            response = stub.ActualizarProducto(producto_pb2.ActualizarProductoRequest(
                id=producto_id,
                nombre="Laptop Gaming Pro Max",
                cantidad=20,
                precio=999990.0,
                sucursal="Casa Matriz"
            ))
            
            if response.exito:
                print(f"✅ {response.mensaje}")
                producto = response.producto
                print(f"   Nombre actualizado: {producto.nombre}")
                print(f"   Precio actualizado: ${producto.precio}")
            else:
                print(f"❌ Error: {response.mensaje}")
            
            # 9. Listar productos final
            print("\n📋 9. Lista final de productos...")
            response = stub.ListarProductos(producto_pb2.ListarProductosRequest(
                pagina=1,
                elementos_por_pagina=20,
                ordenar_por="precio",
                orden="desc"
            ))
            
            if response.exito:
                print(f"✅ {response.mensaje}")
                print(f"📊 Total productos: {response.total_productos}")
                
                for producto in response.productos:
                    print(f"   - {producto.nombre} ({producto.sucursal}) - {producto.cantidad} uds - ${producto.precio}")
            else:
                print(f"❌ Error: {response.mensaje}")
            
            print("\n" + "=" * 50)
            print("🎉 Todas las pruebas completadas exitosamente!")
            print("💡 El servidor gRPC está funcionando correctamente")
            
        except grpc.RpcError as e:
            print(f"❌ Error de gRPC: {e.code()}: {e.details()}")
        except Exception as e:
            print(f"❌ Error inesperado: {str(e)}")

if __name__ == '__main__':
    run() 