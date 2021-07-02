import logging
from typing import Dict, Protocol

from camunda.variables.variables import Variables
from ..utils.utils import Timer


_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class ExternalTaskHandler(Protocol):
    async def complete(
        self, task_id, global_variables: Variables, local_variables: Variables = None
    ):
        ...

    async def failure(self, task_id, error_message, error_details, retries, retry_timeout):
        ...

    async def bpmn_error(self, task_id, error_code):
        ...

    async def extend_lock(self, task_id):
        ...

    async def unlock(self, task_id):
        ...


class ExternalTask:
    def __init__(self, context, handler: ExternalTaskHandler, lock_interval: int):
        self.handler = handler
        self._context = context
        self.local_variables = Variables()
        self.global_variables = Variables()
        self.context_variables = Variables(self._context.get("variables", {}))
        self._timer = None
        if lock_interval:
            # extend lock after 80 percent of the lock duration time has passed
            timeout_ms = lock_interval * 0.8
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

    @property
    def tenant_id(self) -> str:
        return self._context.get("tenantId", None)

    @property
    def business_key(self) -> str:
        return self._context.get("businessKey", None)

    async def complete(self) -> None:
        _LOGGER.info(f"Task {self.task_id} completed")
        if self._timer is not None:
            self._timer.cancel()
        await self.handler.complete(self.task_id, self.global_variables, self.local_variables)

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
        await self.handler.bpmn_error(self.task_id, error_code)

    async def unlock(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
        await self.handler.unlock(self.task_id)

    async def extend_lock(self) -> None:
        await self.handler.extend_lock(self.task_id)
        if self._timer is not None:
            self._timer.reset()

    def _calculate_retries(self, max_retries: int) -> int:
        retries = self._context.get("retries", "")
        retries = int(retries) - 1 if retries else max_retries
        return retries

    def __str__(self) -> str:
        return f"{self._context}"
