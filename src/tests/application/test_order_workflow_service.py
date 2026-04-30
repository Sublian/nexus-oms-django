import logging
import pytest
from unittest.mock import MagicMock

from src.application.services.order_workflow_service import OrderWorkflowService


def _make_order(status, workflow_processed=False):
    # Order stub — sin DB, sin Django ORM. Servicio no debe depender de ellos.
    order = MagicMock()
    order.id = 42
    order.status = status
    order.workflow_processed = workflow_processed
    order.organization = MagicMock()
    order.organization.id = 1
    return order


class TestOrderWorkflowService:

    def setup_method(self):
        self.logger = MagicMock()
        self.mock_usecase = MagicMock()
        self.service = OrderWorkflowService(self.logger, self.mock_usecase)

    def test_happy_path_logs_start_action_end(self):
        # Caso 1 (guia.md): flujo correcto emite START, ACTION_EXECUTED, INVOICING_TRIGGERED, END
        order = _make_order('PAID')

        self.service.handle_order_paid(order)

        log_messages = [call.args[0] for call in self.logger.info.call_args_list]
        assert any('[action=START]' in m for m in log_messages)
        assert any('[action=ACTION_EXECUTED]' in m for m in log_messages)
        assert any('[action=INVOICING_TRIGGERED]' in m for m in log_messages)
        assert any('[action=END]' in m for m in log_messages)

    def test_logs_are_structured_and_filterable(self):
        # Logs deben tener orden_id y action para ser buscables
        order = _make_order('PAID')

        self.service.handle_order_paid(order)

        log_messages = [call.args[0] for call in self.logger.info.call_args_list]
        for msg in log_messages:
            assert '[order_id=42]' in msg
            assert '[action=' in msg

    def test_happy_path_marks_workflow_processed(self):
        # Garantiza que el flag de idempotencia queda en True tras ejecución exitosa
        order = _make_order('PAID')

        self.service.handle_order_paid(order)

        assert order.workflow_processed is True

    def test_idempotency_skips_already_processed(self):
        # Caso 2 (guia.md): segunda llamada no ejecuta — idempotencia persistente en DB
        order = _make_order('PAID', workflow_processed=True)

        self.service.handle_order_paid(order)

        warning_messages = [call.args[0] for call in self.logger.warning.call_args_list]
        assert any('[action=SKIP_ALREADY_PROCESSED]' in m for m in warning_messages)
        self.logger.info.assert_not_called()

    def test_invalid_status_skips_with_warning(self):
        # Caso 3 (guia.md): estado diferente a PAID → skip con warning, sin flujo
        order = _make_order('DRAFT')

        self.service.handle_order_paid(order)

        warning_messages = [call.args[0] for call in self.logger.warning.call_args_list]
        assert any('[action=VALIDATION_FAIL]' in m for m in warning_messages)
        self.logger.info.assert_not_called()

    def test_pending_status_skips(self):
        # PENDING no es PAID — misma guardia, sin excepción
        order = _make_order('PENDING')

        self.service.handle_order_paid(order)

        self.logger.info.assert_not_called()
        assert self.logger.warning.called

    def test_invoicing_trigger_is_called(self):
        # Punto de extensión para Fase 2 — se invoca aunque sea placeholder
        order = _make_order('PAID')

        self.service.handle_order_paid(order)

        log_messages = [call.args[0] for call in self.logger.info.call_args_list]
        invoicing_logs = [m for m in log_messages if 'INVOICING_TRIGGERED' in m]
        assert len(invoicing_logs) == 1
        assert '[order_id=42]' in invoicing_logs[0]

    def test_all_events_logged_in_order(self):
        # Validar secuencia completa: START → ACTION → INVOICING → END
        order = _make_order('PAID')

        self.service.handle_order_paid(order)

        log_messages = [call.args[0] for call in self.logger.info.call_args_list]
        actions = [m.split('[action=')[1].split(']')[0] for m in log_messages if '[action=' in m]

        # Orden correcto: START siempre primero, END siempre último
        assert actions[0] == 'START'
        assert actions[-1] == 'END'
        assert 'ACTION_EXECUTED' in actions
        assert 'INVOICING_TRIGGERED' in actions
