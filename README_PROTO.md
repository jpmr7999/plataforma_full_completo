# 📋 Archivo Proto - Servicios de Productos

## 🎯 **Descripción**
Este archivo `producto.proto` define los servicios gRPC para la gestión de productos en el sistema de ventas.

## 📁 **Archivo:** `producto.proto`

---

## 🚀 **Servicios Disponibles**

### **1. ListarProductos**
```protobuf
rpc ListarProductos (ListarProductosRequest) returns (ListarProductosResponse);
```
**Función:** Obtiene una lista paginada de todos los productos
**Parámetros:** página, elementos_por_pagina, ordenar_por, orden

### **2. CrearProducto**
```protobuf
rpc CrearProducto (CrearProductoRequest) returns (CrearProductoResponse);
```
**Función:** Crea un nuevo producto
**Parámetros:** nombre, cantidad, precio, tipo_sucursal, nombre_sucursal

### **3. ObtenerProducto**
```protobuf
rpc ObtenerProducto (ObtenerProductoRequest) returns (ObtenerProductoResponse);
```
**Función:** Obtiene un producto específico por ID
**Parámetros:** id

### **4. ActualizarProducto**
```protobuf
rpc ActualizarProducto (ActualizarProductoRequest) returns (ActualizarProductoResponse);
```
**Función:** Actualiza los datos de un producto existente
**Parámetros:** id, nombre, cantidad, precio, sucursal

### **5. EliminarProducto**
```protobuf
rpc EliminarProducto (EliminarProductoRequest) returns (EliminarProductoResponse);
```
**Función:** Elimina (soft delete) un producto
**Parámetros:** id

### **6. BuscarProductos**
```protobuf
rpc BuscarProductos (BuscarProductosRequest) returns (BuscarProductosResponse);
```
**Función:** Busca productos por nombre
**Parámetros:** termino_busqueda, pagina, elementos_por_pagina

### **7. ProductosPorSucursal**
```protobuf
rpc ProductosPorSucursal (ProductosPorSucursalRequest) returns (ProductosPorSucursalResponse);
```
**Función:** Obtiene productos de una sucursal específica
**Parámetros:** sucursal, pagina, elementos_por_pagina

### **8. ActualizarStock**
```protobuf
rpc ActualizarStock (ActualizarStockRequest) returns (ActualizarStockResponse);
```
**Función:** Actualiza el stock de un producto
**Parámetros:** id, nueva_cantidad

---

## 📊 **Mensajes Definidos**

### **Producto (Mensaje Principal)**
```protobuf
message Producto {
  int32 id = 1;
  string nombre = 2;
  int32 cantidad = 3;
  double precio = 4;
  string sucursal = 5;
  string fecha_creacion = 6;
  bool activo = 7;
}
```

### **Request/Response Patterns**
Cada servicio tiene su par de mensajes Request/Response:
- `ListarProductosRequest` / `ListarProductosResponse`
- `CrearProductoRequest` / `CrearProductoResponse`
- `ObtenerProductoRequest` / `ObtenerProductoResponse`
- etc.

---

## 🛠 **Cómo Usar el Archivo Proto**

### **1. Generar código Python**
```bash
# Instalar protobuf
pip install grpcio grpcio-tools

# Generar código Python
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. producto.proto
```

### **2. Implementar el servidor gRPC**
```python
import grpc
from concurrent import futures
import producto_pb2
import producto_pb2_grpc

class ProductoService(producto_pb2_grpc.ProductoServiceServicer):
    def ListarProductos(self, request, context):
        # Implementar lógica para listar productos
        pass
    
    def CrearProducto(self, request, context):
        # Implementar lógica para crear producto
        pass
    # ... otros métodos
```

### **3. Implementar el cliente gRPC**
```python
import grpc
import producto_pb2
import producto_pb2_grpc

# Crear canal
channel = grpc.insecure_channel('localhost:50051')
stub = producto_pb2_grpc.ProductoServiceStub(channel)

# Llamar servicio
request = producto_pb2.ListarProductosRequest(pagina=1, elementos_por_pagina=10)
response = stub.ListarProductos(request)
```

---

## 📋 **Ventajas de usar gRPC**

✅ **Comunicación bidireccional** en tiempo real  
✅ **Contratos fuertemente tipados** con protobuf  
✅ **Alto rendimiento** y eficiencia  
✅ **Generación automática** de código cliente/servidor  
✅ **Streaming** de datos  
✅ **Interoperabilidad** entre diferentes lenguajes  

---

## 🔗 **Integración con Django**

Este archivo proto se puede integrar con Django para:
- **API REST** (actual) + **gRPC** (nuevo)
- **Microservicios** independientes
- **Comunicación entre servicios**
- **APIs móviles** de alto rendimiento

**¿Te gustaría que implemente el servidor gRPC en Django o necesitas alguna modificación en el archivo proto?** 