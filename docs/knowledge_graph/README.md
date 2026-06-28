# Knowledge Graph — Nexus OMS

**Fuente de verdad para arquitectura, dominio, seguridad e infraestructura.**

---

## Governance & Standards

⚠️ **Antes de editar o crear nodos, lee ESTOS TRES ARCHIVOS EN ORDEN**:

1. **[GOVERNANCE.md](./GOVERNANCE.md)** — Leyes de creación (¿cuándo nace un nodo?)
2. **[NODE_TYPES.md](./NODE_TYPES.md)** — 7 tipos autorizados (Root, Entity, Domain, Security, ADR, Integration, Roadmap)
3. **[NODE_STYLE_GUIDE.md](./NODE_STYLE_GUIDE.md)** — Contrato mínimo (metadatos + 4 preguntas)

**Plantilla**: [templates/node_template.md](./templates/node_template.md) — copia esto para nodo nuevo.

---

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
```yaml
---
**Estado**: [STABLE | DRAFT | TENSION | DEPRECATED]
**Última actualización**: 2026-06-27
**Responsable**: Tech Lead
**Siguiente nodo recomendado**: [link a siguiente]
```

---

## Navegación

- **[INDEX.md](./INDEX.md)** — Mapa de 8 regiones + puntos de entrada
- **[Decisiones](./decisions/)** — ADRs que justifican cada elección arquitectónica
- **[Proyecto](./project/)** — Roadmap macro + objetivos
- **[Arquitectura](./architecture/)** — Stack técnico + interfaces
- **[Seguridad](./security/)** — S0 (fundación) + S1 (aislación) + S2 (RLS)
- **[Dominio](./domain/)** — Order Lifecycle + reglas de negocio
- **[Infraestructura](./infrastructure/)** — PostgreSQL + Celery + persistencia

---

## Cómo actualizar el grafo

1. **Leer primero**: GOVERNANCE.md → NODE_TYPES.md → NODE_STYLE_GUIDE.md
2. **Editar nodo existente**:
   - Respeta las 4 preguntas
   - Valida links
   - Commit + push
3. **Crear nodo nuevo**:
   - ¿Califica según GOVERNANCE.md? (vida propia, multi-entrada, evolución independiente, no duplica)
   - Usa [templates/node_template.md](./templates/node_template.md)
   - Linkea desde mínimo 1 nodo existente
   - Commit + push
4. **Si edge quebró**: corregir en las 2 direcciones

---

## ⚠️ Sesión Operativa NUNCA va aquí

Este grafo es **conocimiento consolidado** (estable, duradero).

Sesión operativa vive en:
- **`CURRENT_SESSION.md`** — conversación en-vivo, decisiones del turno, TODOs efímeros
- **PR descriptions** — contexto específico del cambio
- **Commit messages** — razonamiento de cada change

No escribas en el grafo cosas como:
- "Hoy decidimos hacer X"
- "Pendiente: testear Y"
- "Próxima sesión: probar Z"

Esas pertenecen a CURRENT_SESSION.md o a un task tracker.

---

## Versionado

Cada cambio → nuevo commit en git. El grafo es parte del repo.

Formato commit:
```
docs: [acción] [nodo] — [breve descripción]

- Detalle 1
- Detalle 2

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
```
