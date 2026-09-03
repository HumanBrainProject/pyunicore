"""
Async client library for UNICORE

For full info on the UNICORE REST API, see
https://unicore-docs.readthedocs.io/en/latest/user-docs/rest-api/index.html
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import re
import time
import typing
from contextlib import asynccontextmanager
from datetime import datetime
from datetime import timedelta
from enum import Enum

import aiofiles
import httpx

from pyunicore.credentials import Anonymous
from pyunicore.credentials import AuthenticationFailedException
from pyunicore.credentials import Credential

_DEFAULT_CACHE_TIME = 5  # in seconds

_FACTORY_RE = r"""
^                                 # start of line
(?P<site_url>\s*https://.*/       # capture full url
(?P<site_name>.*)                 # capture site name
/rest/core/)
.*                                # ignore the rest
"""

_FACTORY_RE = re.compile(_FACTORY_RE, re.VERBOSE)

_WORKFLOWS_RE = r"""
^                                 # start of line
(?P<site_url>\s*https://.*/       # capture full url
(?P<site_name>.*)                 # capture site name
/rest/workflows)
"""

_WORKFLOWS_RE = re.compile(_WORKFLOWS_RE, re.VERBOSE)


def _url_params(offset, num, tags, filter=None):
    """for adding optional paging and tags as query params"""
    q_params = {}
    if offset > 0:
        q_params["offset"] = offset
    if num is not None:
        q_params["num"] = num
    if len(tags) > 0:
        q_params["tags"] = ",".join(map(str, tags))
    if filter is not None:
        q_params["filter"] = filter
    return q_params


class Transport:
    """Handles HTTP calls:
        - adds HTTP Authorization header based on the supplied credentials
        - transparently handles security sessions
        - handles user preferences

    see also
        https://unicore-docs.readthedocs.io/en/latest/user-docs/rest-api/index.html#user-preferences
        https://unicore-docs.readthedocs.io/en/latest/user-docs/rest-api/index.html#security-session-handling
    """

    def __init__(
        self,
        credential: Credential,
        verify=False,
        use_security_sessions=True,
        timeout=120,
        client: httpx.AsyncClient = None,
    ):
        """
        Create a new Transport.

        Args:
            credential: the credential
            verify: if true, SSL verification of the server's certificate will be done
            use_security_sessions: if true, UNICORE's security sessions mechanism
                will be used (to speed up request processing)
            timeout: timeout for HTTP calls (defaults to 120 seconds)
            client: httpx.AsyncClient (if none, a new one will be created)
        """
        super().__init__()
        self.credential = credential
        self.verify = verify
        self.use_security_sessions = use_security_sessions
        self.last_session_id = None
        self._preferences = None
        self.timeout = timeout
        self.settings_changed = True
        self._client = client if client else httpx.AsyncClient(verify=self.verify)

    def _clone(self):
        """create a copy of this transport"""
        tr = Transport(
            self.credential,
            verify=self.verify,
            use_security_sessions=self.use_security_sessions,
            timeout=self.timeout,
            client=self._client,
        )
        tr._preferences = self._preferences
        tr.last_session_id = self.last_session_id
        return tr

    def _headers(self, kwargs):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        auth = self.credential.get_auth_header()
        if auth:
            headers["Authorization"] = auth

        if self.use_security_sessions and self.last_session_id is not None:
            headers["X-UNICORE-SecuritySession"] = self.last_session_id

        if self._preferences is not None:
            headers["X-UNICORE-User-Preferences"] = self._preferences

        if "headers" in kwargs:
            headers.update(kwargs["headers"])
            del kwargs["headers"]

        return headers

    @property
    def preferences(self):
        return self._preferences

    @preferences.setter
    def preferences(self, value):
        self._preferences = value
        self.last_session_id = None
        self.settings_changed = True

    def _check_error(self, res: httpx.Response):
        """checks for error and extracts any error info sent by the server"""
        if 400 <= res.status_code < 600:
            reason = res.reason_phrase
            try:
                reason = res.json().get("errorMessage", "n/a")
            except ValueError:
                pass
            msg = f"{res.status_code} Server Error: {reason} for url: {res.url}"
            raise httpx.HTTPError(msg)
        else:
            res.raise_for_status()

    def _repeat_required(self, res: httpx.Response, headers: dict):
        if self.use_security_sessions:
            if 432 == res.status_code:
                headers.pop("X-UNICORE-SecuritySession", None)
                return True
        return False

    async def run_method(self, method, **args) -> httpx.Response:
        """performs the requested method, handling security sessions, timeouts etc"""
        if (not self._client) or self._client.is_closed:
            # the Transport is often shared, and client may have been closed
            self._client = httpx.AsyncClient(verify=self.verify)
        _headers = self._headers(args)
        res = await method(headers=_headers, timeout=self.timeout, **args)
        if self._repeat_required(res, _headers):
            res = await method(
                headers=_headers,
                timeout=self.timeout,
                **args,
            )
        self._check_error(res)
        if self.use_security_sessions:
            self.last_session_id = res.headers.get("X-UNICORE-SecuritySession", None)
        self.settings_changed = False
        return res

    async def get(self, to_json=True, **kwargs):
        """do GET and return the response content as JSON

        Note:
            For the raw response, set `to_json` to false
        """
        res = await self.run_method(self._client.get, **kwargs)
        if not to_json:
            return res
        return res.json()

    async def put(self, **kwargs):
        """do a PUT and return the response"""
        return await self.run_method(self._client.put, **kwargs)

    async def post(self, **kwargs):
        """do a POST and return the response"""
        return await self.run_method(self._client.post, **kwargs)

    async def delete(self, **kwargs):
        """send a DELETE to the current endpoint and return the response"""
        return await self.run_method(self._client.delete, **kwargs)

    @asynccontextmanager
    async def get_stream(self, **kwargs):
        """do a GET via httpx.stream() and return the response"""
        _headers = self._headers(kwargs)
        _headers.pop("X-UNICORE-SecuritySession", None)
        async with self._client.stream(
            "GET", headers=_headers, timeout=self.timeout, **kwargs
        ) as r:
            yield r


class Resource:
    """Base class for accessing a UNICORE REST endpoint with (cached)
    properties and some common methods.
    """

    def __init__(
        self, security: Credential | Transport, resource_url: str, cache_time=_DEFAULT_CACHE_TIME
    ):
        """
        Create a new Resource.
        Args:
            security: this can be either a Credential or a Transport
            resource_url: the endpoint to connect to
            cache_time: the minimum time in seconds between calls to the endpoint
                    when getting properties
        """
        super().__init__()
        if isinstance(security, Credential):
            self.transport = Transport(security)
        elif isinstance(security, Transport):
            self.transport = security._clone()
        else:
            raise TypeError("Need Credential or Transport object")
        self.resource_url = resource_url
        self.cache_time = cache_time
        self._last_properties = None
        self._last_retrieved = datetime.min

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self.transport:
            await self.aclose()

    async def aclose(self):
        await self.transport._client.aclose()

    @property
    async def properties(self) -> dict:
        """get resource properties (these are cached for cache_time seconds)"""
        now = datetime.now()
        if (
            self.transport.settings_changed
            or self.cache_time <= 0
            or (timedelta(seconds=self.cache_time) < now - self._last_retrieved)
        ):
            self._last_properties = await self.transport.get(url=self.resource_url)
            self._last_retrieved = now
        return self._last_properties

    @property
    async def links(self) -> dict:
        """returns a map with link names mapped to URLs"""
        urls: dict = (await self.properties)["_links"]
        return {k: v["href"] for k, v in urls.items()}

    async def delete(self):
        """delete/destroy this resource"""
        await self.transport.delete(url=self.resource_url)

    async def set_properties(self, props) -> dict:
        """set/update resource properties"""
        return await self.transport.put(url=self.resource_url, json=props).json()

    def __repr__(self):
        return f"Resource: {self.resource_url}"

    __str__ = __repr__


class Registry(Resource):
    """Client for a UNICORE service Registry

        >>> base_url = '...' # e.g. "https://.../rest/registries/default_registry"
        >>> credential = '...'
        >>> registry = Registry(credential, base_url)

    Will collect the BASE URLs of all registered sites
    """

    def __init__(self, security: Credential | Transport, url: str, cache_time=_DEFAULT_CACHE_TIME):
        super().__init__(security, url, cache_time)
        self._site_urls = {}
        self._workflow_services_urls = {}

    @property
    async def site_urls(self):
        self._site_urls = {}
        for entry in (await self.properties)["entries"]:
            # just want the "core" URL and the site ID
            href = entry["href"]
            service_type = entry["type"]
            if "CoreServices" == service_type:
                base = re.match(r"(https://\S+/rest/core).*", href).group(1)
                site_name = re.match(r"https://\S+/(\S+)/rest/core", href).group(1)
                self._site_urls[site_name] = base
        return self._site_urls

    @property
    async def workflow_services_urls(self):
        self._workflow_services_urls = {}
        for entry in (await self.properties)["entries"]:
            # just want the "core" URL and the site ID
            href = entry["href"]
            service_type = entry["type"]
            if "WorkflowServices" == service_type:
                base = re.match(r"(https://\S+/rest/workflows).*", href).group(1)
                site_name = re.match(r"https://\S+/(\S+)/rest/workflows", href).group(1)
                self._workflow_services_urls[site_name] = base
        return self._workflow_services_urls

    async def site(self, name: str):
        """Get a client object for the named site"""
        return Client(self.transport, (await self.site_urls)[name])

    async def workflow_service(self, name: str = None):
        """Get a client object for the named site, or the first in the list if no name is given"""
        if name is None:
            _, url = list((await self.workflow_services_urls).items())[0]
        else:
            url = (await self.workflow_services_urls)[name]
        return WorkflowService(self.transport, url)


class Client(Resource):
    """Entrypoint to the UNICORE API at a site

    >>> base_url = '...' # e.g. "https://localhost:8080/DEMO-SITE/rest/core"
    >>> credential = credentials.UsernamePassword("demouser", "test123")
    >>>
    >>> async with pyunicore.aio.client.Client(credential, base_url) as client:
    >>>     # to get the jobs
    >>>     jobs = await client.get_jobs()
    >>>     # to start a new job:
    >>>     job_description = {...}
    >>>     job = await client.new_job(job_description)
    """

    def __init__(
        self,
        security: Credential | Transport,
        site_url: str,
        cache_time=_DEFAULT_CACHE_TIME,
    ):
        super().__init__(security, site_url, cache_time)

    async def assert_authentication(self):
        '''Asserts that the remote role is not "anonymous"'''
        if not isinstance(self.transport.credential, Anonymous):
            if (await self.access_info)["role"]["selected"] == "anonymous":
                raise AuthenticationFailedException(
                    "Failure to authenticate at %s" % self.resource_url
                )

    @property
    async def access_info(self) -> dict:
        """get authentication and authentication information about the current user"""
        return (await self.properties)["client"]

    @property
    async def server_version_info(self):
        """get server version as a tuple (major, minor, patch)"""
        v: str = (await self.properties)["server"]["version"]
        return tuple([int(x) for x in tuple(v.split("-")[0].split("."))])

    async def get_storages(self, offset=0, num=200, tags=[], all=False) -> list[Storage]:
        """get a list of all Storages on this site
        Use the optional 'offset' and 'num' parameters to handle long result lists
        (for long lists, the server might not return all results!).
        Use the optional tag list to filter the results.
        (UNICORE 10): by default, the storage list will not include any job
        directories. Set the 'all' flag to True to also show job directories.
        """
        filter = "all" if all else None
        q_params = _url_params(offset, num, tags, filter)
        urls = (await self.transport.get(url=(await self.links)["storages"], params=q_params))[
            "storages"
        ]
        return [Storage(self.transport, url) for url in urls]

    async def get_transfers(self, offset=0, num=200, tags=[]) -> list[Transfer]:
        """get a list of all Transfers.
        Use the optional 'offset' and 'num' parameters to handle long result lists
        (for long lists, the server might not return all results!).
        Use the optional tag list to filter the results."""
        q_params = _url_params(offset, num, tags)
        url = (await self.links)["transfers"]
        urls = (await self.transport.get(url=url, params=q_params))["transfers"]
        return [Transfer(self.transport, url) for url in urls]

    async def get_applications(self) -> list[Application]:
        apps = []
        for url in (await self.transport.get(url=(await self.links)["factories"]))["factories"]:
            for app in (await self.transport.get(url=url))["applications"]:
                apps.append(Application(self.transport, url + "/applications/" + app))
        return apps

    async def get_compute(self) -> list[Compute]:
        """get a list of all Compute resources"""
        resources = []
        for url in (await self.transport.get(url=(await self.links)["factories"]))["factories"]:
            resources.append(Compute(self.transport, url))
        return resources

    async def get_jobs(self, offset=0, num=None, tags=[]) -> list[Job]:
        """return a list of `Job` objects.
        Use the optional 'offset' and 'num' parameters to handle long result lists
        (for long lists, the server might not return all results!).
        Use the optional tag list to filter the results."""
        q_params = _url_params(offset, num, tags)
        urls = await self.transport.get(url=(await self.links)["jobs"], params=q_params)["jobs"]
        return [Job(self.transport, url) for url in urls]

    async def new_job(self, job_description: dict, inputs=[], autostart=True) -> Job:
        """Submit and start a job on the site, optionally uploading local input data files
        The input files can be either a simple array of local file names, or a dictionary
        with the destination names as keys and the local file names as values.
        """
        if len(inputs) > 0 or job_description.get("haveClientStageIn") is True:
            job_description["haveClientStageIn"] = "true"
        submission_url = (await self.links)["jobs"]
        resp = await self.transport.post(url=submission_url, json=job_description)
        job_url = resp.headers["Location"]
        job_type: str = job_description.get("Job type", "n/a")
        if "ALLOCATE" == job_type.upper():
            job = Allocation(self.transport, job_url)
        else:
            job = Job(self.transport, job_url)
        if len(inputs) > 0:
            working_dir = await job.working_dir
            for input_item in inputs:
                if isinstance(inputs, dict):
                    await working_dir.upload(inputs[input_item], destination=input_item)
                else:
                    await working_dir.upload(input_item)
        if autostart:
            await job.start()
        return job

    async def execute(self, cmd: str, login_node: str = None) -> Job:
        """run a (non-batch) command on the site, executed on a login node
        Args:
            cmd - the command to run
            login_node - optionally specify the login node to run on
        """
        job_description = {"Executable": cmd, "Job type": "INTERACTIVE"}
        if not login_node:
            job_description["Login node"] = login_node
        resp = await self.transport.post(url=(await self.links)["jobs"], json=job_description)
        return Job(self.transport, resp.headers["Location"])

    async def issue_auth_token(self, lifetime=-1, renewable=False, limited=False) -> str:
        """
        Issue an authentication token (JWT) from this UNICORE server
        Args:
            lifetime: lifetime in seconds. If <=0, the server default will be used
            limited: if True, the token will only be useable on this server
            renewable: if True, the token can be used to get a new token
        """
        url = self.resource_url + "/token"
        params = {}
        if lifetime > 0:
            params["lifetime"] = lifetime
        if renewable:
            params["renewable"] = "true"
        if limited:
            params["limited"] = "true"
        resp = await self.transport.get(
            url=url, headers={"Accept": "text/plain"}, to_json=False, params=params
        )
        return resp.text


class Application(Resource):
    """wrapper around a UNICORE application"""

    def __init__(
        self,
        security: Credential | Transport,
        app_url: str,
        submit_url: str = None,
        cache_time=_DEFAULT_CACHE_TIME,
    ):
        super().__init__(security, app_url, cache_time)
        if submit_url is None:
            submit_url = app_url.split("/rest/core/factories/")[0] + "/rest/core/jobs"
        self.submit_url = submit_url

    @property
    async def name(self):
        return (await self.properties)["ApplicationName"]

    @property
    async def version(self):
        return (await self.properties)["ApplicationVersion"]

    @property
    async def options(self):
        return (await self.properties)["Options"]

    def __repr__(self):
        return f"Application {self.resource_url}"

    __str__ = __repr__


class JobStatus(Enum):
    """UNICORE Job states"""

    UNDEFINED = "UNDEFINED"
    READY = "READY"
    STAGINGIN = "STAGINGIN"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    STAGINGOUT = "STAGINGOUT"
    SUCCESSFUL = "SUCCESSFUL"
    FAILED = "FAILED"

    def ordinal(self):
        i = 0
        for s in JobStatus:
            if s == self:
                return i
            i += 1

    def __repr__(self):
        return self._name_

    __str__ = __repr__


class Job(Resource):
    """wrapper around UNICORE job"""

    def __init__(
        self, security: Credential | Transport, job_url: str, cache_time=_DEFAULT_CACHE_TIME
    ):
        super().__init__(security, job_url, cache_time)

    @property
    def id(self) -> str:
        """get the UUID of this job"""
        return os.path.basename(self.resource_url)

    @property
    async def working_dir(self) -> Storage:
        """return the Storage for accessing this job's working directory"""
        wd = Storage(self.transport, (await self.links)["workingDirectory"])
        if await self.is_running:
            await wd._wait_until_ready(timeout=self.transport.timeout)
        return wd

    @property
    async def status(self) -> JobStatus:
        return JobStatus((await self.properties)["status"])

    @property
    async def bss_details(self) -> dict:
        """return a JSON containing the low-level batch system details"""
        return await self.transport.get(url=self.links["details"])

    @property
    async def exit_code(self) -> int | None:
        x = (await self.properties).get("exitCode", None)
        return int(x) if x else None

    @property
    async def log(self) -> list[str]:
        return (await self.properties)["log"]

    @property
    async def is_running(self):
        """checks whether this job is still running"""
        return (await self.status) not in (JobStatus.SUCCESSFUL, JobStatus.FAILED)

    async def abort(self):
        """abort this job"""
        url = (await self.links)["action:abort"]
        await self.transport.post(url=url, json={})

    async def restart(self):
        """restart this job"""
        url = (await self.links)["action:restart"]
        await self.transport.post(url=url, json={})

    async def start(self):
        """start this job - only required if client had to stage-in local files"""
        url = (await self.links)["action:start"]
        await self.transport.post(url=url, json={})

    async def poll(self, state=JobStatus.SUCCESSFUL, timeout=0):
        """wait until this job reaches the given status (default : SUCCESSFUL)
        or a later one (like SUCCESSFUL or FAILED).
        If the optional timeout is reached, a TimeoutError will be raised
        Args:
            state - job state to wait for (default : JobStatus.SUCCESSFUL)
            timeout - timeout in seconds (default: 0 = no timeout)
        """
        if state == JobStatus.UNDEFINED:
            raise ValueError("Cannot wait for %s" % state)
        if (await self.status).ordinal() >= JobStatus.SUCCESSFUL.ordinal():
            return
        start_time = int(time.time())
        while (await self.status).ordinal() < state.ordinal():
            wait_time = max(2, self.cache_time + 1)
            await asyncio.sleep(wait_time)
            if timeout > 0 and int(time.time()) > start_time + timeout:
                raise TimeoutError("Timeout waiting for job to become %s" % state.value)

    def __repr__(self):
        return f"Job: {self.resource_url}"

    __str__ = __repr__


class Allocation(Job):
    """A special Job representing a batch system allocation. Tasks can be submitted
    'into' the allocation using the new_job() method. Use 'srun' or whichever
    command is suitable for running the task. UNICORE will automatically set the
    correct job ID, so the task is started in the allocation.
    """

    def __init__(
        self, security: Credential | Transport, job_url: str, cache_time=_DEFAULT_CACHE_TIME
    ):
        super().__init__(security, job_url, cache_time)

    async def new_job(self, job_description: dict, inputs=[], autostart=True):
        """submit and start a job within the existing allocation"""
        if not await self.is_ready:
            raise
        if len(inputs) > 0 or job_description.get("haveClientStageIn") is True:
            job_description["haveClientStageIn"] = "true"
        resp = await self.transport.post(url=self.resource_url, json=job_description)
        job_url = resp.headers["Location"]
        job = Job(self.transport, job_url)
        if len(inputs) > 0:
            working_dir = await job.working_dir
            for input_item in inputs:
                await working_dir.upload(input_item)
        if autostart and job_description.get("haveClientStageIn", None) == "true":
            await job.start()
        return job

    async def wait_until_available(self, timeout=0):
        """wait until the allocation is available"""
        await self.poll(JobStatus.RUNNING, timeout)
        start_time = int(time.time())
        wait_time = max(2, self.cache_time + 1)
        while True:
            bss_id = (await self.properties)["batchSystemID"]
            if bss_id.startswith("INTERACTIVE_"):
                await asyncio.sleep(wait_time)
                if timeout > 0 and int(time.time()) > start_time + timeout:
                    raise TimeoutError("Timeout waiting for allocation to become available")
            else:
                break

    @property
    async def is_ready(self):
        """check that the allocation is available for use"""
        return await self.status == JobStatus.RUNNING

    def __repr__(self):
        return f"Allocation: {self.resource_url}"

    __str__ = __repr__


class Compute(Resource):
    """wrapper around a UNICORE compute resource (a specific cluster with queues)"""

    def __init__(
        self, security: Credential | Transport, resource_url: str, cache_time=_DEFAULT_CACHE_TIME
    ):
        super().__init__(security, resource_url, cache_time)

    def __repr__(self):
        return f"Compute: {self.resource_url}"

    __str__ = __repr__

    @property
    async def queues(self):
        return (await self.properties)["resources"]

    async def get_applications(self) -> list[Application]:
        apps = []
        base_url = (await self.links)["applications"]
        for app in (await self.properties)["applications"]:
            apps.append(Application(self.transport, base_url + "/" + app))
        return apps


class Storage(Resource):
    """wrapper around a UNICORE Storage resource"""

    def __init__(
        self, security: Credential | Transport, storage_url: str, cache_time=_DEFAULT_CACHE_TIME
    ):
        super().__init__(security, storage_url, cache_time)

    async def _wait_until_ready(self, timeout=30):
        """since some storages take some time to initialise, this method attempts to wait
        until the storage is READY. If the storage does not become "READY" in the
        given time, or the storage reports an "ERROR" status, an IOError is raised
        """
        i = 0
        while True:
            st = (await self.properties).get("resourceStatus", "n/a")
            if st == "READY":
                break
            if "INITIALIZING" == st:
                await asyncio.sleep(1)
                i += 1
            if "ERROR" == st:
                raise OSError("Storage error")
            if timeout > 0 and i > timeout:
                raise OSError("Timeout waiting for Storage to become useable")

    def _to_file_url(self, path: str):
        return (
            self.resource_url
            + "/files"
            + pathlib.Path("/" + path.lstrip("/")).as_posix().rstrip("/")
        )

    async def contents(self, path: str = "/"):
        """get a simple list of files in the given directory"""
        return await self.transport.get(url=self._to_file_url(path))

    async def stat(self, path: str):
        """get a reference to a file/directory"""
        path_url = self._to_file_url(path)
        headers = {
            "Accept": "application/json",
        }
        props = await self.transport.get(url=path_url, headers=headers)
        if props["isDirectory"]:
            ret = PathDir(self, path_url, path)
        else:
            ret = PathFile(self, path_url, path)
        return ret

    async def listdir(self, base: str = "/") -> dict:
        """get a list of files and directories in the given base directory"""
        ret = {}
        for path, meta in (await self.contents(base))["content"].items():
            path_url = self._to_file_url(path)
            path = path.lstrip("/")
            if meta["isDirectory"]:
                ret[path] = PathDir(self, path_url, path)
            else:
                ret[path] = PathFile(self, path_url, path)
        return ret

    async def rename(self, source: str, target: str):
        """rename a file on this storage"""
        json = {
            "from": source,
            "to": target,
        }
        await self.transport.post(url=self.links["action:rename"], json=json)

    async def copy(self, source: str, target: str):
        """copy a file on this storage"""
        json = {
            "from": source,
            "to": target,
        }
        await self.transport.post(url=self.links["action:copy"], json=json)

    async def mkdir(self, name: str):
        """create a directory"""
        await self.transport.post(url=self._to_file_url(name), json={})

    async def rmdir(self, name: str):
        """remove a directory and all its content"""
        await self.transport.delete(url=self._to_file_url(name))

    async def rm(self, name: str):
        """remove a file"""
        await self.transport.delete(url=self._to_file_url(name))

    async def makedirs(self, name: str):
        """create directory"""
        await self.mkdir(name)

    async def upload(self, file_name: str, destination: str = None):
        """upload local file "file_name" to the remote file "destination".

        Remote directories will be created automatically, if required.
        If "destination" is not given, it is derived from the local
        file path.

        Examples:
        - file_name = "test.txt" -> upload to "test.txt" in the base directory
        of the storage
        - file_name = "/tmp/test.txt" -> upload to "test.txt" in the base directory
        - file_name = "folder1/test.txt" -> upload to "folder1/test.txt",
          automatically creating the "folder1" subdirectory

         Args:
            file_name  : the path to the local file
            destination: (optional) the remote file name / path
        """
        if destination is None:
            if os.path.isabs(file_name):
                destination = os.path.basename(file_name)
            else:
                destination = file_name
        async with aiofiles.open(file_name, "rb") as fd:
            await self.put(source=fd, destination=destination)

    async def put(self, source, destination: str):
        """upload data to the destination file on this storage

        Args:
            source (str-like or (aiofiles) file-like): this will be uploaded
            destination: target path (parent directory will be created if needed)

        """
        _headers = {"Content-Type": "application/octet-stream"}
        r = await self.transport.put(
            url=self._to_file_url(destination), headers=_headers, content=source
        )
        await r.aclose()

    async def send_file(
        self,
        file_name: str,
        remote_url: str,
        protocol: str = None,
        scheduled: str = None,
        additional_parameters: dict = {},
    ):
        """launch a server-to-server transfer: send a file from this storage to a remote location

        Args:
            file_name : the file on this storage to send (supports wildcards)
            remote_url: the destination
                (https://.../rest/core/storages/NAME/files/path_to_file_or_directory)
            protocol: optional protocol (e.g. "UFTP")
            additional_parameters: any protocol-dependent additional settings

        Returns:
            a Transfer object
        """
        params = additional_parameters.copy()
        if protocol:
            remote_url = protocol + ":" + remote_url
        if scheduled:
            params["scheduledStartTime"] = scheduled
        json = {
            "file": file_name,
            "target": remote_url,
            "extraParameters": params,
        }
        dest = self.resource_url + "/transfers"
        resp = await self.transport.post(url=dest, json=json)
        tr_url = resp.headers["Location"]
        return Transfer(self.transport, tr_url)

    async def receive_file(
        self,
        remote_url: str,
        file_name: str,
        protocol: str = None,
        scheduled: str = None,
        additional_parameters: dict = {},
    ):
        """launch a server-to-server transfer: pull a file from a remote storage to this storage

        Args:
            remote_url: the remote file (supports wildcards)
                (https://.../rest/core/storages/NAME/files/path_to_file)
            file_name : the file on this storage to write to
            protocol: optional protocol (e.g. "UFTP")
            additional_parameters: any protocol-dependent additional settings

        Returns:
            a Transfer object
        """
        params = additional_parameters.copy()
        if protocol:
            remote_url = protocol + ":" + remote_url
        if scheduled:
            params["scheduledStartTime"] = scheduled
        json = {
            "file": file_name,
            "source": remote_url,
            "extraParameters": params,
        }
        dest = self.resource_url + "/transfers"
        r = await self.transport.post(url=dest, json=json)
        tr_url = r.headers["Location"]
        return Transfer(self.transport, tr_url)

    def __repr__(self):
        return f"Storage: {self.resource_url}"

    __str__ = __repr__


class Path(Resource):
    """common base for files and directories"""

    def __init__(self, storage: Storage, path_url: str, name: str, cache_time=_DEFAULT_CACHE_TIME):
        super().__init__(storage.transport, path_url, cache_time)
        self.name = name
        self.storage = storage

    @property
    def isdir(self):
        """is a directory"""
        return False

    @property
    def isfile(self):
        """is a file"""
        return False

    @property
    async def size(self):
        return int((await self.properties)["size"])

    async def get_metadata(self, name: str = None):
        if name:
            return (await self.properties)["metadata"][name]
        else:
            return (await self.properties)["metadata"]

    async def remove(self):
        """remove this file or directory"""
        return await self.storage.rm(self.name)

    def __repr__(self):
        return f"{self.__class__.__name__}: {self.name}"

    __str__ = __repr__


class PathDir(Path):
    def __init__(self, storage: Storage, path_url: str, name: str, cache_time=_DEFAULT_CACHE_TIME):
        super().__init__(storage, path_url, name, cache_time)

    @property
    def isdir(self):
        return True

    def __repr__(self):
        return "PathDir: %s" % (self.name)

    __str__ = __repr__


class PathFile(Path):
    def __init__(self, storage: Storage, path_url: str, name: str, cache_time=_DEFAULT_CACHE_TIME):
        super().__init__(storage, path_url, name, cache_time)

    async def download(self, file: str | typing.Any):
        """download file

        Args:
            file_(str or file-like): if a string, a file of that name
            will be created, and filled with the download.  If it's file-like,
            then the contents will be written via write()

            You can also use the raw() method for data streaming purposes

            >>> import cStringIO
            >>> foo = wd.listdir()['foo.txt']
            >>> foo_contents = cStringIO.StringIO()
            >>> foo.download(foo_contents)
            >>> print(foo.contents.getvalue())
        """
        async with self.raw() as resp:
            chunk_size = 10 * 1024
            if isinstance(file, str):
                with open(file, "wb") as fd:
                    async for chunk in resp.aiter_raw(chunk_size):
                        fd.write(chunk)
            else:
                async for chunk in resp.aiter_raw(chunk_size):
                    file.write(chunk)

    @asynccontextmanager
    async def raw(self, offset=0, size=-1):
        """access the raw http response for a streaming download.
        The optional 'offset' and 'size' parameters allow to download only
        part of the file.
        NOTE: this is the raw response from the server and might not be
              decoded appropriately!
        """
        _headers = {"Accept": "application/octet-stream"}
        if offset < 0:
            raise ValueError("Offset must be positive")
        if offset > 0 or size > -1:
            _range = "bytes=%s-" % offset
            if size > -1:
                _range += str(size + offset - 1)
            _headers["Range"] = _range
        async with self.transport.get_stream(url=self.resource_url, headers=_headers) as r:
            yield r

    async def read(self, offset=0, size=-1):
        """read file content into memory"""
        async with self.raw(offset, size) as r:
            return await r.aread()

    @property
    def isfile(self):
        return True


class TransferStatus(Enum):
    """UNICORE server-to-server transfer states"""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    ABORTED = "ABORTED"

    def ordinal(self):
        i = 0
        for s in TransferStatus:
            if s == self:
                return i
            i += 1


class Transfer(Resource):
    """wrapper around a UNICORE server-to-server transfer"""

    def __init__(
        self, security: Credential | Transport, tr_url: str, cache_time=_DEFAULT_CACHE_TIME
    ):
        super().__init__(security, tr_url, cache_time)

    @property
    async def status(self) -> TransferStatus:
        return TransferStatus((await self.properties)["status"])

    @property
    async def is_running(self):
        """checks whether this transfer is still running"""
        return (await self.status) not in (
            TransferStatus.DONE,
            TransferStatus.FAILED,
        )

    @property
    async def transferred_bytes(self):
        """gets the number of transferred bytes"""
        return int((await self.properties)["transferredBytes"])

    async def abort(self):
        """abort this transfer"""
        url = (await self.links)["action:abort"]
        await self.transport.post(url=url, json={})

    async def poll(self, state=TransferStatus.DONE, timeout=0):
        """wait until this transfer reaches the given status (default : DONE)
        or a later one (like FAILED or ABORTED).
        If the optional timeout is reached, a TimeoutError will be raised
        Args:
            state - transfer state to wait for (default : TransferStatus.DONE)
            timeout - timeout in seconds (default: 0 = no timeout)
        """
        start_time = int(time.time())
        while (await self.status).ordinal() < state.ordinal():
            wait_time = max(2, self.cache_time + 1)
            await asyncio.sleep(wait_time)
            if timeout > 0 and int(time.time()) > start_time + timeout:
                raise TimeoutError("Timeout waiting for transfer to become %s" % state.value)

    def __repr__(self):
        return f"Transfer: {self.resource_url}"

    __str__ = __repr__


class WorkflowService(Resource):
    """Entrypoint for the UNICORE Workflow API

    >>> workflows_url = '...' # e.g. "https://localhost:8080/WORKFLOW/rest/workflows"
    >>> credential = ...
    >>> with WorkflowService(credential, workflows_url) as workflow_service:
    >>>     # to get the list of workflows
    >>>     workflows = client.get_workflows()
    >>>     # to start a new workflow:
    >>>     wf_description = {...}
    >>>     wf = await workflow_service.new_workflow(wf_description)
    """

    def __init__(
        self,
        security: Credential | Transport,
        workflows_url: str,
        cache_time=_DEFAULT_CACHE_TIME,
    ):
        super().__init__(security, workflows_url, cache_time)

    @property
    async def access_info(self):
        """get authentication and authentication information about the current user"""
        return (await self.properties)["client"]

    async def assert_authentication(self):
        '''Asserts that the remote role is not "anonymous"'''
        if (await self.access_info)["role"]["selected"] == "anonymous":
            raise AuthenticationFailedException("Failure to authenticate at %s" % self.resource_url)

    async def get_workflows(self, offset=0, num=None, tags=[]) -> list[Workflow]:
        """get the list of workflows.

        Use the optional 'offset' and 'num' parameters to handle long result lists
        (for long lists, the server might not return all results!).
        Use the optional tag list to filter the results."""
        q_params = _url_params(offset, num, tags)
        urls = (await self.transport.get(url=self.resource_url, params=q_params))["workflows"]
        return [Workflow(self.transport, url) for url in urls]

    async def new_workflow(self, wf_description: dict):
        """submit a workflow"""
        resp = await self.transport.post(url=self.resource_url, json=wf_description)
        wf_url = resp.headers["Location"]
        return Workflow(self.transport, wf_url)


class WorkflowStatus(Enum):
    """UNICORE workflow states"""

    UNDEFINED = "UNDEFINED"
    RUNNING = "RUNNING"
    HELD = "HELD"
    SUCCESSFUL = "SUCCESSFUL"
    FAILED = "FAILED"
    ABORTED = "ABORTED"

    def ordinal(self):
        i = 0
        for s in WorkflowStatus:
            if s == self:
                return i
            i += 1


class Workflow(Resource):
    """wrapper around a UNICORE workflow"""

    def __init__(
        self, security: Credential | Transport, wf_url: str, cache_time=_DEFAULT_CACHE_TIME
    ):
        super().__init__(security, wf_url, cache_time)

    @property
    async def status(self) -> WorkflowStatus:
        return WorkflowStatus((await self.properties)["status"])

    @property
    async def parameters(self) -> dict:
        return (await self.properties)["parameters"]

    @property
    async def is_running(self):
        """checks whether this workflow is still running"""
        return (await self.status) not in [
            WorkflowStatus.SUCCESSFUL,
            WorkflowStatus.ABORTED,
            WorkflowStatus.FAILED,
        ]

    @property
    async def is_held(self) -> bool:
        """checks whether this workflow is in HELD state"""
        return (await self.is_running) and ((await self.status) == WorkflowStatus.HELD)

    async def poll(self, state=WorkflowStatus.SUCCESSFUL, timeout=0):
        """wait until this workflow reaches the given status (default : SUCCESSFUL)
        or a later one (like FAILED or ABORTED).
        If the optional timeout is reached, a TimeoutError will be raised
        Args:
            state - transfer state to wait for (default : TransferStatus.DONE)
            timeout - timeout in seconds (default: 0 = no timeout)
        """
        start_time = int(time.time())
        while (await self.status).ordinal() < state.ordinal():
            wait_time = max(2, self.cache_time + 1)
            await asyncio.sleep(wait_time)
            if timeout > 0 and int(time.time()) > start_time + timeout:
                raise TimeoutError("Timeout waiting for transfer to become %s" % state.value)

    async def abort(self):
        """abort this workflow"""
        url = (await self.links)["action:abort"]
        await self.transport.post(url=url, json={})

    async def resume(self, params: dict = {}):
        """resume this workflow (from "HELD" state), optionally updating parameters"""
        url = (await self.links)["action:continue"]
        await self.transport.post(url=url, json=params)

    async def get_files(self) -> dict:
        """get a dictionary of registered workflow files and their
        physical locations
        """
        return await self.transport.get(url=(await self.links)["files"])

    async def get_jobs(self, offset=0, num=None) -> list[Job]:
        """return the list of jobs submitted for this workflow
         Use the optional 'offset' and 'num' parameters to handle long result lists
        (for long lists, the server might not return all results!).
        """
        q_params = _url_params(offset, num, [])
        urls = (await self.transport.get(url=(await self.links)["jobs"], params=q_params))["jobs"]
        return [Job(self.transport, url) for url in urls]

    async def stat(self, path: str) -> Path:
        """lookup the named workflow file and return a PathFile object"""
        physical_location = (await self.get_files())[path]
        storage_url, name = physical_location.split("/files/", 1)
        return await Storage(self.transport, storage_url).stat(name)

    def __repr__(self):
        return f"Workflow: {self.resource_url}"

    __str__ = __repr__
