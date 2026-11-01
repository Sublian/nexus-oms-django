# Pendientes — Fix pago modal + upgrade htmx

Fecha de apertura: 2026-08-09 · Cierre: 2026-11-01

## Contexto
`POST /dashboard/<slug>/orders/<id>/pay/` devolvía 400 con todos los métodos de
pago porque el servidor recibía `method=''`. El input oculto `:value="method"`
del modal nunca se bindeaba.

## Causa raíz (confirmada)
El diagnóstico inicial (Alpine no inicializando el DOM inyectado por HTMX) era
parcial. La causa real:

- `pay_modal.html` renderizaba el JSON de comisiones con `{{ fees_json|safe }}`
  dentro de un atributo HTML con comillas dobles: `x-data="... fees: {...} ..."`.
- El JSON (`{"CASH": 0.0, ...}`) contiene comillas dobles sin escapar, por lo que
  el navegador cerraba el atributo `x-data` en el primer `"`.
- Alpine recibía una expresión truncada (`fees: {`) →
  `Alpine Expression Error: Unexpected token ';'`, `method is not defined`,
  `fee is not defined`.
- Consecuencia: el input `method` quedaba vacío → 400.

El puente `Alpine.initTree()` agregado sigue siendo válido como defensa, pero por
sí solo no resolvía este caso.

## Cambios aplicados
- `layouts/base.html`: htmx `1.9.12` → `2.x` (`@2`; verificado 2.0.11).
- `layouts/base.html`: puente `Alpine.initTree()` en `htmx:afterSwap`.
- `interfaces/web/views.py`: guardia UX — si `method` viene vacío, responder
  `400 'Selecciona un método de pago.'` en vez del mensaje técnico.
- `orders/partials/pay_modal.html`: `fees: {{ fees_json }}` (sin `|safe`) para que
  Django escape las comillas del JSON y el atributo `x-data` quede bien formado.
- `tests/interfaces/web/test_payment_views.py`:
  - `test_pay_without_method_returns_clear_message`
  - `test_pay_modal_escapes_fees_json_for_alpine` (regresión del bug real)

## Verificación (2026-11-01)
- `pytest src/tests/interfaces/web/test_payment_views.py` → **10 passed**
- Suite completa → **395 passed**
- `python manage.py check` → **0 issues**
- E2E real en Chrome headless (Playwright, htmx 2.0.11 + Alpine 3.17.5):
  - modal abre con `method=CASH`, `fee=0`
  - al elegir Tarjeta: `method=CARD`, `fee=28.89` (3.5% de S/ 825.53)
  - submit → orden 256 pasa a `PAGADO`, la fila se actualiza vía OOB swap
  - sin errores de Alpine en consola

## Estado
- [x] Upgrade htmx 2.x
- [x] Puente Alpine↔HTMX
- [x] Defensa backend + test
- [x] Fix de escapado del JSON + test de regresión
- [x] Suite completa y E2E en verde
- [ ] Commit de cierre (cambios aún sin commitear)

### Notas
- `.vscode/settings.json` está modificado pero es ajeno a este fix (tema/entorno).
- `docs/opencode_alcances.md` quedó como documento nuevo sin relación con el fix.
