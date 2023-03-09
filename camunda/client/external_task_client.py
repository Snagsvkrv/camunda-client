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
        "lockDuration": 60000,  # in milliseconds
        "asyncResponseTimeout": 30000,
        "retries": 3,
        "retryTimeout": 30000,
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

    @property
    def lock_duration(self):
        return self.config["lockDuration"]

    @property
    def max_retries(self):
        return self.config["retries"]

    @property
    def retry_timeout(self):
        return self.config["retryTimeout"]

    def get_fetch_and_lock_url(self):
        return f"{self.external_task_base_url}/fetchAndLock"

    async def fetch_and_lock(
        self, topic_names, business_key=None, process_variables=None
    ):
        url = self.get_fetch_and_lock_url()
        body = {
            "workerId": str(
                self.worker_id
            ),  # convert to string to make it JSON serializable
            "maxTasks": self.config["maxTasks"],
            "topics": self._get_topics(topic_names, business_key, process_variables),
            "asyncResponseTimeout": self.config["asyncResponseTimeout"],
        }
        async with self.session.post(
            url, headers=self._get_headers(), json=body
        ) as response:
            await raise_exception_if_not_ok(response)
            return await response.json()

    def _get_topics(self, topic_names, business_key, process_variables):
        topics = []
        for topic in str_to_list(topic_names):
            topic_config = {
                "topicName": topic,
                "lockDuration": self.config["lockDuration"],
                "processVariables": process_variables or {},
            }
            if business_key:
                topic_config["businessKey"] = business_key
            topics.append(topic_config)
        return topics

    async def complete(
        self, task_id, global_variables: Variables, local_variables: Variables
    ):
        url = f"{self.external_task_base_url}/{task_id}/complete"

        body = {
            "workerId": self.worker_id,
            "variables": global_variables.variables,
            "localVariables": local_variables.variables,
        }
        logger.debug("Complete task %s with %s.", task_id, body)
        async with self.session.post(
            url, headers=self._get_headers(), json=body
        ) as response:
            await raise_exception_if_not_ok(response)
            return response.status == HTTPStatus.NO_CONTENT

    async def failure(
        self, task_id, error_message, error_details, retries, retry_timeout
    ):
        url = f"{self.external_task_base_url}/{task_id}/failure"
        body = {
            "workerId": self.worker_id,
            "errorMessage": error_message,
            "retries": retries,
            "retryTimeout": retry_timeout,
        }
        if error_details:
            body["errorDetails"] = error_details

        async with self.session.post(
            url, headers=self._get_headers(), json=body
        ) as response:
            await raise_exception_if_not_ok(response)
            return response.status == HTTPStatus.NO_CONTENT

    async def extend_lock(self, task_id: str) -> None:
        url = f"{self.external_task_base_url}/{task_id}/extendLock"
        logger.debug("Extending lock for %s for %d ms", task_id, self.lock_duration)
        body = {
            "workerId": self.worker_id,
            "newDuration": self.lock_duration,
        }
        async with self.session.post(
            url, headers=self._get_headers(), json=body
        ) as response:
            await raise_exception_if_not_ok(response)
            return response.status == HTTPStatus.NO_CONTENT

    async def unlock(self, task_id: str) -> None:
        url = f"{self.external_task_base_url}/{task_id}/unlock"
        logger.debug("Unlock task %s", task_id)
        try:
            async with self.session.post(
                url, headers=self._get_headers(), json={}
            ) as response:
                await raise_exception_if_not_ok(response)
                return response.status == HTTPStatus.NO_CONTENT
        except Exception as err:
            logger.warning("Unlocking task failed: %s", err)

    async def bpmn_error(self, task_id, error_code):
        url = f"{self.external_task_base_url}/{task_id}/bpmnError"
        body = {
            "workerId": self.worker_id,
            "errorCode": error_code,
        }

        async with self.session.post(
            url, headers=self._get_headers(), json=body
        ) as response:
            response.raise_for_status()
            return response.status == HTTPStatus.NO_CONTENT

    def _get_headers(self):
        return {"Content-Type": "application/json"}
