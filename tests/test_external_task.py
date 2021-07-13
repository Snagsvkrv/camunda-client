import pytest
from pytest_mock import MockerFixture

from camunda.external_task.external_task import ExternalTask


@pytest.fixture
def context():
    return dict(workerId=1, id=1, topicName="TestTopic")


def test_create_task(context, mocker: MockerFixture):
    task = ExternalTask(context)
    assert task.task_id == context["id"]
    assert task.worker_id == context["workerId"]
    assert task.topic_name == context["topicName"]


@pytest.mark.asyncio
async def test_task_complete(context, mocker: MockerFixture):
    task = ExternalTask(context)
    res = task.complete()


@pytest.mark.asyncio
async def test_task_fail(context, mocker: MockerFixture):
    error_message = "NotImplementedError"
    error_details = "This method has not been implemented"
    max_retries = 3
    retry_timeout = 5
    task = ExternalTask(context)
    res = task.failure(
        error_message=error_message,
        error_details=error_details,
        max_retries=max_retries,
        retry_timeout=retry_timeout,
    )


@pytest.mark.asyncio
async def test_task_bpmn_error(context, mocker: MockerFixture):
    task = ExternalTask(context)
    res = task.bpmn_error("de.ubi.nca.RuntimeException")


# @pytest.mark.asyncio
# async def test_create_session_with_username(rpc_server, mocker):
#     mocker.patch("avikom_services.services.definitions.session.start_process")
#     async with AsyncChannelContext(f"{Config.SERVICES_IP}:{Config.SERVICES_PORT}") as channel:
#         session: Result = await SessionServiceStub(channel).StartSession(
#             SessionQuery(username="alex@avikom.app")
#         )
#     mock: Mock = avikom_services.services.definitions.session.start_process
#     assert mock.called
#     args, kwargs = mock.call_args
#     variables: Dict[str, str] = args[2] if len(args) > 2 else kwargs["variables"]
#     assert variables["userId"] == 2
#     assert session.success
