import logging
import glob
from os.path import basename, splitext
from http import HTTPStatus
from aiohttp import FormData, ClientSession

from camunda.utils.response_utils import raise_exception_if_not_ok

logger = logging.getLogger(__name__)

ENGINE_LOCAL_BASE_URL = "http://localhost:8080/engine-rest"


class EngineClient:
    def __init__(self, session: ClientSession, engine_base_url=ENGINE_LOCAL_BASE_URL):
        self.engine_base_url = engine_base_url
        self.session = session

    def get_start_process_instance_url(self, process_key, tenant_id=None):
        if tenant_id:
            return f"{self.engine_base_url}/process-definition/key/{process_key}/tenant-id/{tenant_id}/start"
        return f"{self.engine_base_url}/process-definition/key/{process_key}/start"

    async def start_process(
        self, process_key, variables, tenant_id=None, business_key=None
    ):
        url = self.get_start_process_instance_url(process_key, tenant_id)
        body = {"variables": variables}
        if business_key:
            body["businessKey"] = business_key
        async with self.session.post(
            url, headers=self._get_headers(), json=body
        ) as response:
            await raise_exception_if_not_ok(response)
            return await response.json()

    async def get_process_instance(
        self,
        process_ids=None,
        process_key=None,
        variables=None,
        tenant_ids=None,
        business_key=None,
    ):
        url = f"{self.engine_base_url}/process-instance"
        url_params = self.__get_process_instance_url_params(
            process_ids or [],
            process_key or "",
            tenant_ids or [],
            variables or {},
            business_key,
        )
        async with self.session.get(
            url, headers=self._get_headers(), params=url_params
        ) as response:

            await raise_exception_if_not_ok(response)
            return await response.json()

    async def upload_definition(self, path):
        if "*" in path:
            paths = glob.glob(path)
        else:
            paths = [path]

        for p in paths:
            base_name = basename(p)
            no_ext, _ = splitext(base_name)
            data = FormData()
            data.add_field(
                "file", open(p, "rb"), filename=base_name, content_type="text/xml"
            )
            data.add_field("deployment-name", no_ext)
            data.add_field("deployment-source", "external-task-client-python")
            data.add_field("deploy-changed-only", "true")
            logger.info("uploading %s", base_name)
            async with self.session.post(
                f"{self.engine_base_url}/deployment/create", data=data
            ) as response:
                if response.status == HTTPStatus.BAD_REQUEST:
                    reason = await response.json()
                    raise Exception(reason)
                elif response.status != HTTPStatus.OK:
                    response.raise_for_status()

    async def send_message(
        self, message_name, correlation_keys=None, process_variables=None, business_key=None
    ):
        body = {
            "messageName": message_name,
            "correlationKeys": correlation_keys or {},
            "processVariables": process_variables or {},
        }
        if business_key:
            body["businessKey"] = business_key
        async with self.session.post(
            f"{self.engine_base_url}/message", json=body
        ) as response:
            if response.status == HTTPStatus.OK:
                return await response.json()
            elif response.status == HTTPStatus.BAD_REQUEST:
                raise Exception(await response.json()["message"])
            else:
                response.raise_for_status()

    async def stop_processes(
        self, process_ids=None, tenant_ids=None, business_key=None
    ):
        params = dict(skipCustomListeners="true", skipIoMappings="true")
        process_instances_url = f"{self.engine_base_url}/process-instance"
        if not process_ids:
            processes = await self.get_process_instance(
                tenant_ids=tenant_ids, business_key=business_key
            )
            process_ids = [elem["id"] for elem in processes]
        for process_id in process_ids:
            async with self.session.delete(
                f"{process_instances_url}/{process_id}", params=params
            ) as response:
                if response.status == HTTPStatus.BAD_REQUEST:
                    raise Exception(await response.json()["message"])
                elif response.status not in [HTTPStatus.OK, HTTPStatus.NOT_FOUND]:
                    response.raise_for_status()

    def __get_process_instance_url_params(
        self, process_ids, process_key, tenant_ids, variables, business_key
    ):
        url_params = {}
        process_ids_filter = ",".join(process_ids)
        if process_ids_filter:
            url_params["processInstanceIds"] = process_ids_filter
        if process_key:
            url_params["processDefinitionKey"] = process_key
        variables_filter = ",".join([f"{k}_eq_{v}" for k, v in variables.items()])
        if variables_filter:
            url_params["variables"] = variables_filter
        tenant_ids_filter = ",".join(tenant_ids)
        if tenant_ids_filter:
            url_params["tenantIdIn"] = tenant_ids_filter
        if business_key:
            url_params["businessKey"] = business_key
        return url_params

    def _get_headers(self):
        return {"Content-Type": "application/json"}
