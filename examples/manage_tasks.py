import aiohttp
import asyncio

from camunda.external_task.external_task import ExternalTask, TaskResult, Variables
from camunda.external_task.external_task_worker import ExternalTaskWorker


class Worker:
    def __init__(self):
        self.worker = None
        self.loop = None

    def start(self):
        """Run the worker and block forever"""
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self._run())

    async def _run(self):
        async with aiohttp.ClientSession() as session:
            self.worker = ExternalTaskWorker(
                worker_id=4, base_url="http://localhost:8080/engine-rest", session=session
            )
            # dispatch the first subscription
            self.loop.create_task(
                self.worker.subscribe(topic_names="NumberCheckTask", action=number_check)
            )
            # and block the current task with the second subscription again
            await self.worker.subscribe(topic_names="EchoTask", action=echo)

    def stop(self):
        self.loop.run_until_complete(self._quit())

    async def _quit(self):
        """Cancels the running subcriptions"""
        self.worker.cancel()
        # We wait until there is only one asynchronous task left since this will be
        # the very same task that we are currently running.
        print("stopping ...")
        running_tasks = len(asyncio.all_tasks())
        while running_tasks > 1:
            print(f"waiting for {running_tasks - 1} subscriptions to return ...")
            await asyncio.sleep(5)
            running_tasks = len(asyncio.all_tasks())
        print("stopped")


async def number_check(task: ExternalTask) -> TaskResult:
    try:
        number = task.get_variable("number")
        task.set_variable
        print(f"We received {number} for checking...")
        variables = Variables()
        variables.set_variable(
            "result", "true" if int(number) % 2 != 0 else "false", Variables.ValueType.STRING
        )
        return tsask.complete(local_variables=variables)
    except Exception as err:
        print(f"Oh no! Something went wrong: {err}")
        return task.failure()


async def echo(task: ExternalTask) -> TaskResult:
    print(f"Camunda wants to say: {task.get_variable('text')}")
    return task.complete()


# run the main task
try:
    worker = Worker()
    worker.start()
except KeyboardInterrupt:
    worker.stop()
