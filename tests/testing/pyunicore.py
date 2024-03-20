from typing import Dict
from typing import List


class FakeTransport:
    def __init__(self, auth_token: str = "test_token", oidc: bool = True):
        self.auth_token = auth_token
        self.oidc = oidc

    def _clone(self) -> "FakeTransport":
        return self

    def get(self, url):
        return {"entries": [{"href": "test-entry-url", "type": "test-entry-type"}]}


class FakeRegistry:
    def __init__(
        self,
        transport: FakeTransport,
        url: str = "test_registry_url",
        contains: Dict[str, str] = None,
    ):
        self.transport = transport
        self.url = url
        self.site_urls = contains or {}

    @property
    def properties(self) -> dict:
        return self.__dict__


class FakeJob:
    def __init__(
        self,
        transport: FakeTransport,
        job_url: str = "test-job",
        properties: Dict = None,
        existing_files: Dict[str, str] = None,
        will_be_successful: bool = True,
    ):
        self.transport = transport
        self.url = job_url
        self._properties = properties or {"status": "QUEUED"}
        self._existing_files = existing_files or {}
        self._successful = will_be_successful

    @property
    def properties(self) -> Dict:
        return self._properties

    @property
    def job_id(self) -> str:
        return self.url

    def poll(self) -> None:
        self._properties["status"] = "SUCCESSFUL" if self._successful else "FAILED"

    def abort(self):
        pass


class FakeClient:
    def __init__(
        self,
        transport: FakeTransport = None,
        site_url: str = "test_api_url",
        login_successful: bool = False,
    ):
        if transport is None:
            transport = FakeTransport()
        self.transport = transport
        self.site_url = site_url
        self._properties = {"client": {"xlogin": {}}}
        if login_successful:
            self.add_login_info({"test_login": "test_logged_in"})

    @property
    def properties(self) -> Dict:
        return {**self.__dict__, **self._properties}

    def add_login_info(self, login: Dict) -> None:
        self._properties["client"]["xlogin"] = login

    def new_job(self, job_description: Dict, inputs: List) -> FakeJob:
        return FakeJob(transport=self.transport, job_url="test_job_url")
