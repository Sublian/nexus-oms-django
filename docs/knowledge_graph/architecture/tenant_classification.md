---
id: architecture-tenant-classification
type: architecture
status: approved
reviewed_in: S2.0C
tags: [architecture, multi-tenancy]
---

# Clasificación de Aislamiento Multi-Tenant

Esta matriz establece el modelo de aislamiento para los dominios funcionales del sistema, sirviendo como el contrato arquitectónico de negocio antes de cualquier diseño de implementación técnica.

## ⚖️ Reglas de Gobernanza

1. La clasificación se realiza por responsabilidad de negocio, no por implementación física. El Grafo documenta el negocio; la implementación solo aparece cuando aporta contexto.
2. Los subdominios, componentes derivados y tablas físicas heredan automáticamente la clasificación de su dominio raíz.
3. Los detalles técnicos o limitaciones de la persistencia nunca redefinen una clasificación de negocio.
4. Toda modificación de esta clasificación debe quedar documentada y justificada.

## 🗺️ Matriz de Clasificación por Dominios

| Dominio | Clasificación | Justificación |
| :--- | :--- | :--- |
| **Usuarios** | 🔄 **Híbrido** | Existe un SuperAdmin global para la gestión del SaaS y usuarios aislados por organización. |
| **Ventas y Pedidos** | 🎯 **Tenant** | Cada venta, pedido y pago pertenece exclusivamente a una organización. No hay consolidación cruzada en el núcleo transaccional. |
| **Inventario** | 🎯 **Tenant** | El stock, los movimientos de almacén y los almacenes físicos nunca se comparten entre empresas. |
| **Compras** | 🎯 **Tenant** | Cada empresa administra sus propios proveedores, catálogos de compra y órdenes de reabastecimiento. |
| **Contabilidad** | 🎯 **Tenant** | Cada organización mantiene libros contables independientes por responsabilidad legal y de negocio. |
| **Facturación** | 🎯 **Tenant** | Cada organización emite sus comprobantes con su propia identidad tributaria y credenciales ante la entidad fiscal. |
| **Configuración Global** | 🌐 **Global** | Parámetros compartidos del SaaS que son comunes y legibles por todas las organizaciones. |

## 📈 Evolución

Este documento sirve como referencia para:
- Seguridad
- Permisos
- Persistencia

No define implementación técnica.

## 🔗 Ver también

- ← [README.md](../README.md) (Arquitectura Raíz)
- ← [domain/usuarios.md](../domain/usuarios.md) (Primer Nodo de Dominio)
