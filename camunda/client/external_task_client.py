import logging
from http import HTTPStatus

from camunda.client.engine_client import ENGINE_LOCAL_BASE_URL
from camunda.utils.response_utils import raise_exception_if_not_ok
from camunda.utils.utils import str_to_list
from camunda.variables.variables import Variables

logger = logging.getLogger(__name__)


class ExternalTaskClient:
    default_config = {
        "maxTasks": 1,
        "lockDuration": 300000,  # in milliseconds
        "asyncResponseTimeout": 30000,
        "retries": 3,
        "retryTimeout": 300000,
    }

    def __init__(
        self, worker_id, session, engine_base_url=ENGINE_LOCAL_BASE_URL, config=None
    ):
        self.worker_id = worker_id
        self.external_task_base_url = engine_base_url + "/external-task"
        self.config = self.default_config.copy()
        if config is not None:
            self.config.update(config)
        self.session = session

    def get_fetch_and_lock_url(self):
        return f"{self.external_task_base_url}/fetchAndLock"

    async def fetch_and_lock(self, topic_names, process_variables=None):
        url = self.get_fetch_and_lock_url()
        body = {
            "workerId": str(self.worker_id),  # convert to string to make it JSON serializable
            "maxTasks": self.config["maxTasks"],
            "topics": self._get_topics(topic_names, process_variables),
            "asyncResponseTimeout": self.config["asyncResponseTimeout"],
        }

        async with self.session.post(url, headers=self._get_headers(), json=body) as response:
            await raise_exception_if_not_ok(response)
            return await response.json()

    def _get_topics(self, topic_names, process_variables):
        topics = []
        for topic in str_to_list(topic_names):
            topics.append(
                {
                    "topicName": topic,
                    "lockDuration": self.config["lockDuration"],
                    "processVariables": process_variables or {},
                }
            )
        return topics

    async def complete(self, task_id, global_variables, local_variables={}):
        url = self.get_task_complete_url(task_id)

        body = {
            "workerId": self.worker_id,
            "variables": Variables.format(global_variables),
            "localVariables": Variables.format(local_variables),
        }

        async with self.session.post(url, headers=self._get_headers(), json=body) as response:
            await raise_exception_if_not_ok(response)
            return response.status == HTTPStatus.NO_CONTENT

    def get_task_complete_url(self, task_id):
        return f"{self.external_task_base_url}/{task_id}/complete"

    async def failure(self, task_id, error_message, error_details, retries, retry_timeout):
        url = self.get_task_failure_url(task_id)
        logger.info(f"setting retries to: {retries} for task: {task_id}")
        body = {
            "workerId": self.worker_id,
            "errorMessage": error_message,
            "retries": retries,
            "retryTimeout": retry_timeout,
        }
        if error_details:
            body["errorDetails"] = error_details

        async with self.session.post(url, headers=self._get_headers(), json=body) as response:
            await raise_exception_if_not_ok(response)
            return response.status == HTTPStatus.NO_CONTENT

    def get_task_failure_url(self, task_id):
        return f"{self.external_task_base_url}/{task_id}/failure"

    async def bpmn_failure(self, task_id, error_code):
        url = self.get_task_bpmn_error_url(task_id)

        body = {
            "workerId": self.worker_id,
            "errorCode": error_code,
        }

        async with self.session.post(url, headers=self._get_headers(), json=body) as response:
            response.raise_for_status()
            return response.status == HTTPStatus.NO_CONTENT

    def get_task_bpmn_error_url(self, task_id):
        return f"{self.external_task_base_url}/{task_id}/bpmnError"

    def _get_headers(self):
        return {"Content-Type": "application/json"}
