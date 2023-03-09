import asyncio
from asyncio import Task
import logging
from typing import Callable, List, Dict, Awaitable
from functools import partial

from .external_task import ExternalTask
from .external_task_result import ExternalTaskResult
from ..client.external_task_client import (
    ExternalTaskClient,
    ENGINE_LOCAL_BASE_URL,
)
from ..utils.utils import Timer, get_exception_detail

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class ExternalTaskWorker:
    DEFAULT_SLEEP_SECONDS = 300

    def __init__(
        self,
        worker_id,
        session,
        base_url=ENGINE_LOCAL_BASE_URL,
        config=None,
        business_key=None,
    ):
        self.worker_id = worker_id
        self.client = ExternalTaskClient(self.worker_id, session, base_url, config)
        self.config = config or {}
        self.cancelled = False
        self.business_key = business_key
        self.run_locks: List[asyncio.Lock] = []
        self.task_dict: Dict[str, Task] = {}
        _LOGGER.info("Created new External Task Worker")

    async def subscribe(self, topic_names, action, process_variables=None):
        _LOGGER.info("Subscribing to topic %s", topic_names)
        lock = asyncio.Lock()
        self.run_locks.append(lock)
        await lock.acquire()
        while not self.cancelled:
            _LOGGER.debug("Locked for %s", topic_names)
            await self._fetch_and_execute_safe(topic_names, action, process_variables)
        unlock_tasks = []
        _LOGGER.info("Cancellation requested.")
        for task_id, task in self.task_dict.items():
            task.cancel()
            unlock_tasks.append(self.client.unlock(task_id))
        if unlock_tasks:
            await asyncio.wait(unlock_tasks)
        lock.release()
        _LOGGER.info("Worker stopped.")

    async def cancel(self):
        self.cancelled = True
        await asyncio.wait([lock.acquire() for lock in self.run_locks])
        for lock in self.run_locks:
            lock.release()
        self.run_locks.clear()
        return

    async def _fetch_and_execute_safe(
        self, topic_names, action, process_variables=None
    ):
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
        _LOGGER.debug(
            f"Fetching and Locking external tasks for Topics: {topic_names} "
            f"with process variables: {process_variables}"
        )
        return await self.client.fetch_and_lock(
            topic_names,
            self.business_key,
            process_variables,
        )

    def _parse_response(self, resp_json, topic_names):
        tasks = []
        if resp_json:
            for context in resp_json:
                task = ExternalTask(context)
                tasks.append(task)
        _LOGGER.debug(f"{len(tasks)} External task(s) found for Topics: {topic_names}")
        return tasks

    async def _execute_tasks(self, tasks: List[ExternalTask], action):
        for task in tasks:
            if task.task_id in self.task_dict:
                self.task_dict[task.task_id].cancel()
            self.task_dict[task.task_id] = asyncio.create_task(
                self._execute_task(task, action)
            )

    async def _execute_task(
        self,
        task: ExternalTask,
        action: Callable[[ExternalTask], Awaitable[ExternalTaskResult]],
    ) -> None:
        _LOGGER.info(
            f"Executing external task {task.task_id} for Topic: {task.topic_name}"
        )

        lock_duration = (
            self.config.get("lockDuration", 0)
            if self.config.get("autoExtendLock", False)
            else 0
        )

        # try to extend lock after 80% of the lock duration has been passed
        timer = (
            Timer(
                lock_duration * 0.8 / 1000,
                partial(self.client.extend_lock, task.task_id),
                loop=True,
            )
            if lock_duration
            else None
        )
        try:
            res = await action(task)
            _LOGGER.debug("Task %s is done!", task.task_id)
        except asyncio.CancelledError:
            _LOGGER.info("Task %s has been cancelled.", task.task_id)
            if timer is not None:
                timer.cancel()
            return
        except BaseException as err:
            res = task.failure(
                error_message=type(err).__name__,
                error_details=str(err),
                max_retries=self.client.max_retries,
                retry_timeout=self.client.retry_timeout,
            )
            _LOGGER.error(
                f"[{self.worker_id}][{task.topic_name}] - {get_exception_detail(err)}"
            )
            logging.exception(err)
        if timer is not None:
            timer.cancel()
        try:
            if res.is_success():
                await self.client.complete(
                    res.task.task_id,
                    global_variables=res.task.global_variables,
                    local_variables=res.task.local_variables,
                )
            elif res.is_failure():
                _LOGGER.warning(
                    f"{res.task.task_id} failed. Retry in {res.retry_timeout} ms. {res.retries} left."
                )

                await self.client.failure(
                    res.task.task_id,
                    error_message=res.error_message,
                    error_details=res.error_details,
                    retries=res.retries,
                    retry_timeout=res.retry_timeout,
                )
        except Exception as err:
            _LOGGER.error(
                f"[{self.worker_id}][{task.topic_name}] - {get_exception_detail(err)}"
            )
            logging.exception(err)
        del self.task_dict[task.task_id]

    def _get_sleep_seconds(self):
        return self.config.get("sleepSeconds", self.DEFAULT_SLEEP_SECONDS)

    # async def unlock(self) -> None:
    #     if self._timer is not None:
    #         self._timer.cancel()
    #     await self.handler.unlock(self.task_id)

    # async def extend_lock(self) -> None:
    #     await self.handler.extend_lock(self.task_id)
    #     if self._timer is not None:
    #         self._timer.reset()
