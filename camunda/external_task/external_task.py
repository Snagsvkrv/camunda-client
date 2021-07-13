import logging
from re import I
from typing import Optional
from dataclasses import dataclass

from camunda.variables.variables import Variables
from .external_task_result import ExternalTaskResult

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class ExternalTask:
    def __init__(self, context):
        self._context = context
        self.local_variables = Variables()
        self.global_variables = Variables()
        self.context_variables = Variables(self._context.get("variables", {}))

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

    def complete(self) -> ExternalTaskResult:
        return ExternalTaskResult(self, success=True)

    def failure(
        self, error_message: str, error_details: str, max_retries: int, retry_timeout: int
    ) -> ExternalTaskResult:
        return ExternalTaskResult(
            self,
            success=False,
            error_message=error_message,
            error_details=error_details,
            retries=self._calculate_retries(max_retries),
            retry_timeout=retry_timeout,
        )

    def bpmn_error(self, error_code: str) -> ExternalTaskResult:
        return ExternalTaskResult(self, success=False, bpmn_error_code=error_code)

    def _calculate_retries(self, max_retries: int) -> int:
        retries = self._context.get("retries", "")
        retries = int(retries) - 1 if retries else max_retries
        return retries

    def __str__(self) -> str:
        return f"{self._context}"
