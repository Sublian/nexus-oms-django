# Knowledge Graph — Nexus OMS

**Fuente de verdad para arquitectura, dominio, seguridad e infraestructura.**

## Directivas de lectura (INMUTABLES)

### 1. Un Concepto = Un Nodo
No duplicar textos. Si un nodo necesita info de otro → usa enlaces `[Texto](../ruta/nodo.md)`.

### 2. Estándar de 4 Preguntas
Cada nodo responde exclusivamente a:
- **¿Qué es?** Definición precisa.
- **¿Por qué existe?** Trigger + motivación.
- **¿Con qué se relaciona?** Edges hacia nodos relacionados.
- **¿Qué sigue?** Recomendación del siguiente nodo.

### 3. Bloque de Cierre Obligatorio
```
---
**Estado**: [STABLE | DRAFT | TENSION | DEPRECATED]
**Última actualización**: 2026-06-27
**Responsable**: Tech Lead
**Siguiente nodo recomendado**: [link a siguiente]
```

## Navegación

- **[INDEX.md](./INDEX.md)** — Mapa de 8 regiones + puntos de entrada
- **[Decisiones](./decisions/)** — ADRs que justifican cada elección arquitectónica
- **[Proyecto](./project/)** — Roadmap macro + objetivos
- **[Arquitectura](./architecture/)** — Stack técnico + interfaces
- **[Seguridad](./security/)** — S0 (fundación) + S1 (aislación) + S2 (RLS)
- **[Dominio](./domain/)** — Order Lifecycle + reglas de negocio
- **[Infraestructura](./infrastructure/)** — PostgreSQL + Celery + persistencia

## Cómo actualizar el grafo

1. Leer [`graph_skeleton`](../feeds0.md) para orientación rápida
2. Editar nodo relevante (respetando 4 preguntas)
3. Si nuevo concepto → crear nodo + linked desde vecino existente
4. Si edge rotos → corregir en las 2 direcciones

## Versionado

Cada cambio → nuevo commit en git. El grafo es parte del repo.
