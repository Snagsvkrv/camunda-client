import aiohttp
import asyncio

from camunda.external_task.external_task import ExternalTask, Variables
from camunda.external_task.external_task_worker import ExternalTaskWorker
from camunda.external_task.external_task_result import ExternalTaskResult


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
        self.loop.run_until_complete(self.worker.cancel())


async def number_check(task: ExternalTask) -> ExternalTaskResult:
    try:
        number = task.context_variables["number"]
        print(f"We received {number} for checking...")
        task.local_variables.set_variable(
            "result", "true" if int(number) % 2 != 0 else "false", Variables.ValueType.STRING
        )
        return task.complete()
    except Exception as err:
        print(f"Oh no! Something went wrong: {err}")
        return task.failure()


async def echo(task: ExternalTask) -> ExternalTaskResult:
    print(f"Camunda wants to say: {task.context_variables['text']}")
    await asyncio.sleep(1000)
    return task.complete()


# run the main task
try:
    worker = Worker()
    worker.start()
except KeyboardInterrupt:
    # Stopping workers might take a while.
    # How long it will take depends on the chosen asyncResponseTimeout (default is 30000)
    print(f"Stopping workers...")
    worker.stop()
print(f"All done!")
