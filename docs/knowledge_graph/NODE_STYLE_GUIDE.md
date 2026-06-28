# NODE_STYLE_GUIDE — Contract Minimal

**Objetivo**: Cada nodo responde 4 preguntas + metadatos. Nada más, nada menos.

## Contrato Obligatorio (MUST HAVE)

Todo nodo `.md` en el grafo debe tener:

### 1. Metadatos (YAML front-matter)
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

### 2. Título
```markdown
# [Título Descriptivo]
```

### 3. Las 4 Preguntas
```markdown
## ¿Qué es?
[Definición precisa, máx 200 palabras]

## ¿Por qué existe?
[Motivación + trigger que lo justifica]

## ¿Con qué se relaciona?
← [entrada] — descripción breve
→ [salida] — descripción breve

## ¿Qué sigue?
[Siguiente nodo recomendado]
```

### 4. Bloque de Cierre
```markdown
---

**Estado**: [STABLE|DRAFT|TENSION]
**Última actualización**: YYYY-MM-DD
**Responsable**: Role
**Siguiente nodo recomendado**: [link]
```

---

## Contrato Opcional (NICE TO HAVE)

Según contexto del nodo:

### Para Nodos Domain/Entity
```markdown
## Invariantes
[Lista bullet de reglas críticas]

## Archivos Relacionados
- `src/path/file.py` → [breve descripción]
```

### Para Nodos Security/ADR
```markdown
## Alternativas Rechazadas
[Por qué NO otras opciones]

## Implicaciones
[Consecuencias positivas/negativas]
```

### Para Nodos de Roadmap/Integration
```markdown
## Timeline
| Fase | Fecha | Status |
|------|-------|--------|
| ... | ... | ... |

## Criterios de Éxito
- [ ] Criterio 1
- [ ] Criterio 2
```

---

## Style Rules

1. **Markdown**: GFM (tables, code blocks, links)
2. **Longitud**: 300-1000 palabras (no ensayos)
3. **Links**: Relativos a otros nodos, no URLs hardcodeadas
4. **Código**: Pseudocódigo o snippets muy cortos (no copiar source)
5. **Tone**: Declarativo, no imperativo ("Order FSM is", no "Implement Order FSM")

---

## Checklist Antes de Publicar

- [ ] Metadatos YAML completos
- [ ] Las 4 preguntas respondidas
- [ ] Links internos validan (grep -r o manual)
- [ ] Nodo no duplica contenido existente
- [ ] Edge desde vecino existente (o incluido en mismo batch)
- [ ] Fecha `last_review` es hoy

---

**Versión**: 1.0
**Efectiva desde**: 2026-06-27
**Próxima revisión**: 2026-07-31
