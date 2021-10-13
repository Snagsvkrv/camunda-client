"""
camunda.external_task_result
============================
"""


from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..external_task import ExternalTask


@dataclass
class ExternalTaskResult:

    task: "ExternalTask"
    success: bool = False
    bpmn_error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[str] = None
    retries: int = 0
    retry_timeout: int = 300000

    def is_success(self):
        return (
            self.success and self.bpmn_error_code is None and self.error_message is None
        )

    def is_failure(self):
        return (
            not self.success
            and self.error_message is not None
            and not self.is_bpmn_error()
        )

    def is_bpmn_error(self):
        return not self.success and self.bpmn_error_code

    def __str__(self) -> str:
        if self.is_success():
            return f"success: task_id={self.task.task_id}, global_variables={self.task.global_variables}, local_variables={self.task.local_variables}"
        elif self.is_failure():
            return (
                f"failure: task_id={self.task.task_id}, "
                f"error_message={self.error_message}, error_details={self.error_details if self.error_details is not None else {}}, "
                f"retries={self.retries}, retry_timeout={self.retry_timeout}"
            )
        elif self.is_bpmn_error():
            return f"bpmn_error: task_id={self.task.task_id}, error_code={self.bpmn_error_code}"
        return "empty_task_result"
