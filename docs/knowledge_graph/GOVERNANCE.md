# GOVERNANCE — Knowledge Graph Creation Laws

**Objetivo**: Mantener grafo limpio, navegable, sin duplicación. Reglas mínimas para MVP.

## Ley 1: Birth Criteria (¿Cuándo nace un nodo?)

Un nodo NUEVO **nace solo si**:

1. **Vida propia**: Concepto que existe independiente de otros
   - ❌ "El JWT tiene 1h TTL" → va en nodo JWT existente
   - ✅ "JWT Token Lifecycle" → su propio nodo (diferentes contextos lo necesitan)

2. **Multi-entrada**: Se referencia desde 2+ nodos distintos
   - ❌ "Detalles obscuros de serializer X" → nota interna
   - ✅ "Order Serialization Contract" → usado por API + Web

3. **Evolución independiente**: Cambia por razones distintas a sus vecinos
   - ❌ "Campo `updated_at` en Order" → va en Order node
   - ✅ "Audit Trail Design" → cuando audit cambia sin que Order cambie

4. **No duplica información**: No existe ya en otro nodo
   - Check: `grep -r "concepto" docs/knowledge_graph/` antes de crear

## Ley 2: Naming Convention

Archivo = `kebab-case-corto.md` (max 40 caracteres)

```
✅ order-fsm.md
✅ tenant-isolation-mechanism.md
✅ invoice-sync-queue-backoff.md
❌ OrderFiniteStateMachine.md (CamelCase)
❌ how-orders-transition-between-states.md (demasiado largo)
```

## Ley 3: No Orphans

Todo nodo nuevo = linkado desde mínimo 1 vecino existente en el mismo batch.

```
Bad:  Crear payment-retry-logic.md sin que otro nodo lo refiera
Good: Crear payment-retry-logic.md + editar invoice-sync-queue.md para linkearlo
```

## Ley 4: Edges Over Hierarchy

No hay carpetas para "niveles" conceptuales. Carpetas solo por dominio (project/, domain/, etc).

Relaciones viven en edges (→ / ←), no en jerarquía de directorios.

```
Bad:  docs/knowledge_graph/domain/order/fsm/states.md
Good: docs/knowledge_graph/domain/order-fsm.md + linkeado desde domain/root.md
```

## Ley 5: Review Triggers

Revisar grafo si:
- Comit toca un nodo existente → check si edge quebró
- PR introduce nueva feature → ¿nuevo nodo o edit existente?
- Bug fix afecta invariante → actualizar Governance/nodo relevante

---

**Responsable**: Tech Lead
**Última revisión**: 2026-06-27
**Próximo review**: Después de primer commit con nuevo nodo
