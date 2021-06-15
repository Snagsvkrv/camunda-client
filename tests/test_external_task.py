import pytest
from pytest_mock import MockerFixture

from camunda.external_task.external_task import ExternalTask


@pytest.fixture
def context():
    return dict(workerId=1, id=1, topicName="TestTopic")


def test_create_task(context, mocker: MockerFixture):
    task = ExternalTask(context, None)
    assert task.task_id == context["id"]
    assert task.worker_id == context["workerId"]
    assert task.topic_name == context["topicName"]


@pytest.mark.asyncio
async def test_task_complete(context, mocker: MockerFixture):
    handler = mocker.AsyncMock()
    task = ExternalTask(context, handler)
    await task.complete()
    assert handler.complete.called
    assert not handler.failure.called
    call = handler.complete.call_args
    assert call.args[0] == context["id"]


@pytest.mark.asyncio
async def test_task_fail(context, mocker: MockerFixture):
    error_message = "NotImplementedError"
    error_details = "This method has not been implemented"
    max_retries = 3
    retry_timeout = 5
    handler = mocker.AsyncMock()
    task = ExternalTask(context, handler)
    await task.failure(
        error_message=error_message,
        error_details=error_details,
        max_retries=max_retries,
        retry_timeout=retry_timeout,
    )
    assert not handler.complete.called
    assert handler.failure.called
    args = handler.failure.call_args.args
    assert args[1] == error_message
    assert args[4] == retry_timeout


@pytest.mark.asyncio
async def test_task_bpmn_error(context, mocker: MockerFixture):
    handler = mocker.AsyncMock()
    task = ExternalTask(context, handler)
    await task.bpmn_error("de.ubi.nca.RuntimeException")
    assert not handler.complete.called
    assert handler.bpmn_error.called
    assert handler.bpmn_error.call_args.args[0] == "de.ubi.nca.RuntimeException"


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
