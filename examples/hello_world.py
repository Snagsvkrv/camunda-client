import aiohttp
import asyncio

from camunda.external_task.external_task import ExternalTask
from camunda.external_task.external_task_worker import ExternalTaskWorker

import logging


async def main():
    # let's create an async http context with aiohttp
    # aiohttp will close the connection when the worker returns (it won't though)
    async with aiohttp.ClientSession() as session:
        # We create a worker with a task id and pass the http session as well as the REST endpoint of Camunda.
        # You need to change 'base_url' in case your Camunda engine is configured differently.
        worker = ExternalTaskWorker(
            worker_id=1,
            base_url="http://localhost:8080/engine-rest",
            session=session,
            config={"lockDuration": 1000, "autoExtendLock": True, "asyncResponseTimeout": 5000},
        )
        print("waiting for a task ...")
        # Subscribe is an async function which will block until the worker is cancelled with `worker.cancel()`,
        # In this example, no one will do this. We will stop the program with Ctrl+C instead
        # When the worker detects a new task for the topic assigned to `topic_name` it will trigger the
        # function/method passed to `action`.
        await worker.subscribe(topic_names="HelloWorldTask", action=process)


# this will be called when a task for the subscribed topic is available
async def process(task: ExternalTask) -> None:
    print("I got a task!")
    # To communicate the successfull processing of a task, we await `task.complete`.
    # If we call `task.failure` instead, Camunda will publish the task again until
    # some client finally completes it or the maximum amount of retries is reached.
    await asyncio.sleep(3)
    await task.complete()
    # await task.failure("Foo", "Some message", 3, 1000)


# run the main task
logging.basicConfig(level=logging.DEBUG)
asyncio.run(main())

