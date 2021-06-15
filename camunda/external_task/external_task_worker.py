import asyncio
from asyncio import tasks, Task
import logging
import inspect
from typing import Callable, List, Dict

from camunda.client.external_task_client import (
    ExternalTaskClient,
    ENGINE_LOCAL_BASE_URL,
)
from camunda.external_task.external_task import ExternalTask
from camunda.utils.utils import get_exception_detail

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class ExternalTaskWorker:
    DEFAULT_SLEEP_SECONDS = 300

    def __init__(self, worker_id, session, base_url=ENGINE_LOCAL_BASE_URL, config=None):
        self.worker_id = worker_id
        self.client = ExternalTaskClient(self.worker_id, session, base_url, config)
        self.config = config or {}
        self.cancelled = False
        self.task_dict: Dict[str, Task] = {}
        _LOGGER.info("Created new External Task Worker")

    async def subscribe(self, topic_names, action, process_variables=None):
        _LOGGER.info(f"Subscribing to topic {topic_names}")
        while not self.cancelled:
            await self._fetch_and_execute_safe(topic_names, action, process_variables)
        _LOGGER.info("Stopping worker")

    def cancel(self):
        self.cancelled = True

    async def _fetch_and_execute_safe(self, topic_names, action, process_variables=None):
        try:
            await self.fetch_and_execute(topic_names, action, process_variables)
        except Exception as e:
            sleep_seconds = self._get_sleep_seconds()
            _LOGGER.warn(
                f"[{self.worker_id}][{topic_names}] - error {get_exception_detail(e)} while fetching tasks "
                f"with process variables: {process_variables}. Retry after {sleep_seconds}."
            )
            await asyncio.sleep(sleep_seconds)

    async def fetch_and_execute(self, topic_names, action, process_variables=None):
        resp_json = await self._fetch_and_lock(topic_names, process_variables)
        tasks = self._parse_response(resp_json, topic_names)
        await self._execute_tasks(tasks, action)

    async def _fetch_and_lock(self, topic_names, process_variables=None):
        _LOGGER.info(
            f"Fetching and Locking external tasks for Topics: {topic_names} "
            f"with process variables: {process_variables}"
        )
        return await self.client.fetch_and_lock(topic_names, process_variables)

    def _parse_response(self, resp_json, topic_names):
        tasks = []
        if resp_json:
            for context in resp_json:
                task = ExternalTask(context, self.client, self.config.get("autoExtendLock", False))
                tasks.append(task)
        _LOGGER.info(f"{len(tasks)} External task(s) found for Topics: {topic_names}")
        return tasks

    async def _execute_tasks(self, tasks: List[ExternalTask], action):
        for task in tasks:
            if task.task_id in self.task_dict:
                self.task_dict[task.task_id].cancel()
            self.task_dict[task.task_id] = asyncio.create_task(self._execute_task(task, action))

    async def _execute_task(self, task: ExternalTask, action: Callable):
        try:
            _LOGGER.info(f"Executing external task {task.task_id} for Topic: {task.topic_name}")
            future = action(task)
            if inspect.isawaitable(future):
                await future
        except Exception as err:
            await task.failure(
                error_message=type(err).__name__,
                error_details=str(err),
                max_retries=self.client.max_retries,
                retry_timeout=10000,
            )
            _LOGGER.error(f"[{self.worker_id}][{task.topic_name}] - {get_exception_detail(err)}")
        del self.task_dict[task.task_id]

    def _get_sleep_seconds(self):
        return self.config.get("sleepSeconds", self.DEFAULT_SLEEP_SECONDS)
