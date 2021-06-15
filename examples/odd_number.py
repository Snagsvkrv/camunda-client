import aiohttp
import asyncio

from camunda.external_task.external_task import ExternalTask, Variables
from camunda.external_task.external_task_worker import ExternalTaskWorker


async def main():
    async with aiohttp.ClientSession() as session:
        # a new parameter! We can pass 'asyncResponseTimeout' to Camunda to configure how long a 'fetch and lock' connection
        # is kept alive. If this value is rather large, clients do not need to reconnect that often but it will take longer for a
        # worker to properly shut down. The default value is 30 seconds (300000)
        worker = ExternalTaskWorker(
            worker_id=4,
            base_url="http://localhost:8080/engine-rest",
            session=session,
            config={"asyncResponseTimeout": 5000},  # wait 5 seconds before timeout
        )
        # Our worker will now subscribe to two topics now
        # We will create a new task with `asyncio.create_task` and await only the second subscribe
        asyncio.create_task(worker.subscribe(topic_names="NumberCheckTask", action=number_check))
        await worker.subscribe(topic_names="EchoTask", action=echo)


async def number_check(task: ExternalTask) -> None:
    try:
        number = task.get_variable("number")
        task.set_variable
        print(f"We received {number} for checking...")
        # we create a Variables object to hand to the task object for completion
        variables = Variables()
        # we set the variable 'result' to 'true' or 'false'
        variables.set_variable(
            "result", "true" if int(number) % 2 != 0 else "false", Variables.ValueType.STRING
        )
        # We pass the variables object as LOCAL variables which will only be available in the context of the task
        # that called the external task worker. The result must be assigned in case it should be used somewhere else.
        # Just have a look at the odd_number.bpmn to see how.
        await task.complete(local_variables=variables)
    # If your input could not be parsed with `int()` the task will fail
    # and another external service could try to do better.
    except Exception as err:
        print(f"Oh no! Something went wrong: {err}")
        await task.failure()


async def echo(task: ExternalTask) -> None:
    print(f"Camunda wants to say: {task.get_variable('text')}")
    await task.complete()


# run the main task
asyncio.run(main())
