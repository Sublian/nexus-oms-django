---
id: domain-usuarios
type: Domain
status: draft
owner: tech-lead
last_review: 2026-06-27
tags: [domain, auth, multi-tenancy]
---

# Usuarios

## Propósito

Gestiona la identidad de los usuarios del sistema.

## Qué debe recordar un operador

- Existe un SuperAdmin global (`superadmin@nexus.com`).
- No todos los usuarios pertenecen a una organización de manera obligatoria.
- Este componente es crítico para el aislamiento multi-tenant del MVP.

## Estado actual

- La columna `organization_id` permite valores nulos (`NULL`).
- Es un comportamiento esperado del MVP para permitir la administración global del SaaS.

## Riesgos conocidos

- Existe riesgo latente si futuras consultas e implementaciones ignoran el contexto de la organización activa.
- La mitigación formal pertenece al roadmap de seguridad del Sector S2 y no forma parte de este nodo.

## Persistencia

Tabla principal:
- `domain_customuser` (Columna `organization_id` tipo `uuid`, Nullable: `YES`)

Tablas relacionadas:
- `domain_customuser_groups`
- `domain_customuser_user_permissions`

## Ver también

- ← [security/root.md](../security/root.md) (Seguridad S1)
- ← [decisions/ADR-001.md](../decisions/ADR-001.md) (Why Application Guards BEFORE PostgreSQL RLS)
- ← [README.md](../README.md) (Arquitectura)
