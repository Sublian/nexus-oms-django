# Node Template — Use This as Skeleton

**Instrucciones**: Copia este archivo, renómbralo, completa las secciones marcadas.

---

```yaml
---
id: node-identifier
type: [Root|Entity|Domain|Security|ADR|Integration|Roadmap]
status: [draft|active|stable]
owner: tech-lead
last_review: 2026-06-27
tags: []
---
```

# [Título del Nodo]

**Propósito**: Una línea sobre qué es y por qué importa.

---

## ¿Qué es?

[Definición clara y precisa. 100-200 palabras máximo.
Explica el concepto de forma que alguien nuevo al proyecto lo entienda.]

### Estructura (si es Entity)
```
[Diagrama ASCII o tabla si es modelo]
```

---

## ¿Por qué existe?

[Motivación que justifica este nodo.
- Qué problema resuelve?
- Qué invariante protege?
- Qué patrón implementa?]

**Trigger**: [foundation|surprise|tension|decision|consequence|hypothesis]

---

## ¿Con qué se relaciona?

← [Nodo Entrante] — [Descripción breve del edge]
← [Nodo Entrante 2] — [Descripción breve]

→ [Nodo Saliente] — [Descripción breve]
→ [Nodo Saliente 2] — [Descripción breve]

---

## Invariantes (Opcional, para Entity/Domain/Security)

```
1. [Invariante 1]
2. [Invariante 2]
3. [Invariante 3]
```

---

## Alternativas Rechazadas (Opcional, para ADR/Decision)

### Opción A: [Alternativa]
❌ Rechazada porque: [razón concisa]

### Opción B: [Alternativa]
❌ Rechazada porque: [razón concisa]

---

## Timeline (Opcional, para Roadmap)

| Fase | Hito | Status |
|------|------|--------|
| S2.0 | Foundation | ✅ Done |
| S2.1 | Design | 🔄 In Progress |
| S2.2 | Implementation | ⏳ Planned |

---

## Success Criteria (Opcional, para Roadmap)

- [ ] Criterio 1
- [ ] Criterio 2
- [ ] Criterio 3

---

## Referencias (Opcional)

- Archivo relacionado: `src/path/file.py`
- ADR relacionado: [ADR-XXX](../decisions/ADR-XXX.md)
- Nodo padre: [Parent Node](../domain/parent-node.md)

---

## ¿Qué sigue?

[Nombre del próximo nodo recomendado que leer]

→ [Siguiente Nodo](../domain/siguiente-nodo.md)

---

**Estado**: draft
**Última actualización**: 2026-06-27
**Responsable**: Tech Lead
**Siguiente nodo recomendado**: [Link al siguiente]
