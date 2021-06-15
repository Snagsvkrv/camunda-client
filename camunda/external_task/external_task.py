import logging

from camunda.client.external_task_client import ExternalTaskClient
from camunda.variables.variables import Variables
from ..utils.utils import Timer


_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class ExternalTask:
    def __init__(self, context, handler: ExternalTaskClient, extend_lock: bool):
        self.handler = handler
        self._context = context
        self._variables = Variables(context.get("variables", {}))
        self._timer = None
        if extend_lock:
            # extend lock after 80 percent of th ethe lock duration time has passed
            timeout_ms = handler.lock_duration * 0.8
            self._timer = Timer(timeout_ms / 1000, self.extend_lock)

    @property
    def worker_id(self) -> str:
        return self._context["workerId"]

    @property
    def task_id(self) -> str:
        return self._context["id"]

    @property
    def topic_name(self) -> str:
        return self._context["topicName"]

    def get_variable(self, variable_name):
        return self._variables.get_variable(variable_name)

    def set_variable(self, variable_name, variable_value, variable_type=None) -> None:
        self._variables.set_variable(variable_name, variable_value, variable_type)

    @property
    def tenant_id(self) -> str:
        return self._context.get("tenantId", None)

    async def complete(self, local_variables: Variables = None) -> None:
        _LOGGER.info(f"Task {self.task_id} completed")
        _LOGGER.debug(f"\nGlobals: {self._variables.to_dict()}\nLocals: {local_variables}")
        if self._timer is not None:
            self._timer.cancel()
        await self.handler.complete(self.task_id, self._variables, local_variables)

    async def failure(
        self, error_message: str, error_details: str, max_retries: int, retry_timeout: int
    ) -> None:
        _LOGGER.warn(f"Task {self.task_id} failed with {error_message}")
        _LOGGER.debug(f"Message: {error_details}")

        if self._timer is not None:
            self._timer.cancel()
        retries = self._calculate_retries(max_retries)
        _LOGGER.debug(f"setting retries to: {retries} and timeout for {retry_timeout} ms")
        await self.handler.failure(
            self.task_id, error_message, error_details, retries, retry_timeout
        )

    async def bpmn_error(self, error_code: str) -> None:
        _LOGGER.warn(f"Task {self.task_id} caused an BPMN error with code {error_code}")
        if self._timer is not None:
            self._timer.cancel()
        await self.handler.bpmn_error(error_code)

    async def extend_lock(self) -> None:
        await self.handler.extend_lock(self.task_id)
        self._timer.reset()

    def _calculate_retries(self, max_retries: int) -> int:
        retries = self._context.get("retries")
        retries = int(retries - 1) if retries else max_retries
        return retries

    def __str__(self) -> str:
        return f"{self._context}"
