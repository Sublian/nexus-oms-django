---
id: architecture-security-glossary
type: architecture
status: approved
reviewed_in: S2.1
tags: [architecture, security, glossary]
---

# Lenguaje Ubicuo de Seguridad (S2.1)

Este documento establece el glosario oficial y los términos inequívocos que gobernarán el modelado de seguridad y el comportamiento del control de accesos en Nexus OMS.

## 📖 Glosario de Términos

| Concepto | Significado del Negocio |
| :--- | :--- |
| **Organización** | Empresa o MYPE dueña absoluta de sus propios datos e inventarios. |
| **Usuario** | Persona natural autenticada de manera única en la plataforma. |
| **Actor** | El rol o nivel de confianza con el que un Usuario ejecuta acciones sobre el sistema (`SuperAdmin`, `Administrador`, `Operador`). |
| **Contexto** | La Organización activa e identificada durante la ejecución de una transacción. |
| **Dominio** | Área funcional y de negocio específica de la plataforma (ej. Ventas, Compras). |
| **Recurso** | Objeto o entidad de negocio protegido contra accesos cruzados (ej. un Pedido, un Almacén). |
| **Operación** | Acción concreta de negocio que un Actor realiza sobre un Recurso (ej. Registrar Venta). |

## ⚖️ Invariantes de Control Básicas

- **1 Usuario : 1 Organización** (Excepto el `SuperAdmin` del SaaS).
- Los recursos de tipo **Global** pertenecen a la administración del SaaS, los Tenants solo los consumen de forma pasiva.
- La seguridad se hereda a través de la secuencia de la **Operación**, no por configuraciones manuales en las tablas hijas.

## 🔗 Ver también

- ← [architecture/tenant_classification.md](tenant_classification.md) (Matriz de Dominios Aprobada)
- ← [README.md](../README.md) (Arquitectura Raíz)
