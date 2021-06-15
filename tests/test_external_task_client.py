from camunda.variables.variables import Variables
import pytest
import aiohttp
from camunda.client.external_task_client import ExternalTaskClient


@pytest.fixture
def context():
    return dict(workerId=1, id=1, topicName="TestTopic")


class MockResponse:
    def __init__(self, text, status):
        self._text = text
        self.status = status

    async def text(self):
        return self._text

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def __aenter__(self):
        return self


@pytest.fixture
async def session():
    session = aiohttp.ClientSession()
    yield session
    await session.close()


async def test_create_task(mocker, session):
    client = ExternalTaskClient("TestWorker", session)
    taskId = "Task01"
    mock = mocker.patch("aiohttp.ClientSession.post", return_value=MockResponse("{}", 200))
    await client.complete(taskId, Variables())
    assert mock.called
    post_url = mock.call_args.args[0]
    kwargs = mock.call_args.kwargs
    assert kwargs["json"] == dict(workerId="TestWorker", localVariables={}, variables={})
    assert post_url == f"http://localhost:8080/engine-rest/external-task/{taskId}/complete"
    await client.complete(taskId + "a", Variables({""}))

