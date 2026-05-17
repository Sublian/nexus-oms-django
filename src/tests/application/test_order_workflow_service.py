import pytest
from unittest.mock import MagicMock

from src.application.services.order_workflow_service import OrderWorkflowService


def _make_order(status, workflow_processed=False):
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
        self.service = OrderWorkflowService(self.logger)
        # Patchear metodos que tocan DB o Celery — unit tests sin infraestructura
        self.service._claim_workflow_lock = MagicMock(return_value=True)
        self.service._trigger_invoicing = MagicMock()

    def test_happy_path_logs_start_action_end(self):
        order = _make_order('PAID')

        self.service.handle_order_paid(order)

        log_messages = [call.args[0] for call in self.logger.info.call_args_list]
        assert any('[action=START]' in m for m in log_messages)
        assert any('[action=ACTION_EXECUTED]' in m for m in log_messages)
        assert any('[action=END]' in m for m in log_messages)

    def test_logs_are_structured_and_filterable(self):
        order = _make_order('PAID')

        self.service.handle_order_paid(order)

        log_messages = [call.args[0] for call in self.logger.info.call_args_list]
        for msg in log_messages:
            assert '[order_id=42]' in msg
            assert '[action=' in msg

    def test_happy_path_marks_workflow_processed(self):
        order = _make_order('PAID')

        self.service.handle_order_paid(order)

        assert order.workflow_processed is True

    def test_idempotency_skips_already_processed(self):
        # Fast-path: objeto en memoria con workflow_processed=True — no llega al DB lock
        order = _make_order('PAID', workflow_processed=True)

        self.service.handle_order_paid(order)

        warning_messages = [call.args[0] for call in self.logger.warning.call_args_list]
        assert any('[action=SKIP_ALREADY_PROCESSED]' in m for m in warning_messages)
        self.logger.info.assert_not_called()
        self.service._claim_workflow_lock.assert_not_called()

    def test_skips_if_db_lock_not_claimed(self):
        # DB lock devuelve False: otro worker ya proceso la orden (race condition prevenida)
        order = _make_order('PAID')
        self.service._claim_workflow_lock = MagicMock(return_value=False)

        self.service.handle_order_paid(order)

        warning_messages = [call.args[0] for call in self.logger.warning.call_args_list]
        assert any('[action=SKIP_ALREADY_PROCESSED]' in m for m in warning_messages)
        self.logger.info.assert_not_called()

    def test_invalid_status_skips_with_warning(self):
        order = _make_order('DRAFT')

        self.service.handle_order_paid(order)

        warning_messages = [call.args[0] for call in self.logger.warning.call_args_list]
        assert any('[action=VALIDATION_FAIL]' in m for m in warning_messages)
        self.logger.info.assert_not_called()

    def test_pending_status_skips(self):
        order = _make_order('PENDING')

        self.service.handle_order_paid(order)

        self.logger.info.assert_not_called()
        assert self.logger.warning.called

    def test_invoicing_trigger_is_called(self):
        # _trigger_invoicing debe ser invocado una vez con la orden
        order = _make_order('PAID')

        self.service.handle_order_paid(order)

        self.service._trigger_invoicing.assert_called_once_with(order)

    def test_all_events_logged_in_order(self):
        # START siempre primero, END siempre ultimo
        order = _make_order('PAID')

        self.service.handle_order_paid(order)

        log_messages = [call.args[0] for call in self.logger.info.call_args_list]
        actions = [m.split('[action=')[1].split(']')[0] for m in log_messages if '[action=' in m]

        assert actions[0] == 'START'
        assert actions[-1] == 'END'
        assert 'ACTION_EXECUTED' in actions

    def test_claim_lock_called_once_on_happy_path(self):
        order = _make_order('PAID')

        self.service.handle_order_paid(order)

        self.service._claim_workflow_lock.assert_called_once_with(order)

    def test_workflow_status_failed_on_error(self):
        # Si un paso interno falla, workflow_status = 'failed'
        order = _make_order('PAID')
        self.service._log_order_paid = MagicMock(side_effect=ValueError("boom"))

        with pytest.raises(ValueError):
            self.service.handle_order_paid(order)

        assert order.workflow_status == 'failed'
        error_messages = [call.args[0] for call in self.logger.error.call_args_list]
        assert any('[action=ERROR]' in m for m in error_messages)
