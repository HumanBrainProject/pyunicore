"""
    Client library for UNICORE

    For full info on the UNICORE REST API, see
    https://unicore-docs.readthedocs.io/en/latest/user-docs/rest-api/index.html
"""

try:
    from urllib3 import disable_warnings

    disable_warnings()
except ImportError:
    pass

from contextlib import closing
from datetime import datetime, timedelta
from enum import Enum

import os
import pathlib
import re
import requests
import time

import pyunicore.credentials

_DEFAULT_CACHE_TIME = 5  # in seconds

_HBP_REGISTRY_URL = "https://hbp-unic.fz-juelich.de:7112" "/HBP/rest/registries/default_registry"

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
    """wrapper around requests, which
        - adds HTTP Authorization header based on the supplied credentials
        - transparently handles security sessions
        - handles user preferences

    see also
        https://unicore-docs.readthedocs.io/en/latest/user-docs/rest-api/index.html#user-preferences
        https://unicore-docs.readthedocs.io/en/latest/user-docs/rest-api/index.html#security-session-handling
    """

    def __init__(
        self,
        credential: pyunicore.credentials.Credential,
        verify=False,
        use_security_sessions=True,
        timeout=120,
    ):
        """
        Create a new Transport.

        Args:
            credential: the credential
            timeout: timeout for HTTP calls (defaults to 120 seconds)
            use_security_sessions: if true, UNICORE's security sessions mechanism
                will be used (to speed up request processing)
            verify: if true, SSL verification of the server's certificate will be done
        """
        super().__init__()
        self.credential = credential
        self.verify = verify
        self.use_security_sessions = use_security_sessions
        self.last_session_id = None
        self._preferences = None
        self.timeout = timeout
        self.settings_changed = True

    def _clone(self):
        """create a copy of this transport"""
        tr = Transport(self.credential)
        tr._preferences = self._preferences
        tr.use_security_sessions = self.use_security_sessions
        tr.last_session_id = self.last_session_id
        tr.timeout = self.timeout
        tr.verify = self.verify
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

    def check_error(self, res):
        """checks for error and extracts any error info sent by the server"""
        if 400 <= res.status_code < 600:
            reason = res.reason
            try:
                reason = res.json().get("errorMessage", "n/a")
            except ValueError:
                pass
            msg = f"{res.status_code} Server Error: {reason} for url: {res.url}"
            raise requests.HTTPError(msg, response=res)
        else:
            res.raise_for_status()

    def repeat_required(self, res, headers):
        if self.use_security_sessions:
            if 432 == res.status_code:
                headers.pop("X-UNICORE-SecuritySession", None)
                return True
        return False

    def run_method(self, method, **args):
        """performs the requested method, handling security sessions, timeouts etc"""
        _headers = self._headers(args)
        res = method(headers=_headers, verify=self.verify, timeout=self.timeout, **args)
        if self.repeat_required(res, _headers):
            res = method(
                headers=_headers,
                verify=self.verify,
                timeout=self.timeout,
                **args,
            )
        self.check_error(res)
        if self.use_security_sessions:
            self.last_session_id = res.headers.get("X-UNICORE-SecuritySession", None)
        self.settings_changed = False
        return res

    def get(self, to_json=True, **kwargs):
        """do GET and return the response content as JSON

        Note:
            For the raw response, set `to_json` to false
        """
        res = self.run_method(requests.get, **kwargs)
        if not to_json:
            return res
        json = res.json()
        res.close()
        return json

    def put(self, **kwargs):
        """do a PUT and return the response"""
        return self.run_method(requests.put, **kwargs)

    def post(self, **kwargs):
        """do a POST and return the response"""
        return self.run_method(requests.post, **kwargs)

    def delete(self, **kwargs):
        """send a DELETE to the current endpoint"""
        self.run_method(requests.delete, **kwargs).close()


class Resource:
    """Base class for accessing a UNICORE REST endpoint with (cached)
    properties and some common methods.
    """

    def __init__(self, security, resource_url, cache_time=_DEFAULT_CACHE_TIME):
        """
        Create a new Resource.
        Args:
            security: this can be either a Credential or a Transport
            resource_url: the endpoint to connect to
            cache_time: the minimum time in seconds between calls to the endpoint
                    when getting properties
        """
        super().__init__()
        if isinstance(security, pyunicore.credentials.Credential):
            self.transport = Transport(security)
        elif isinstance(security, Transport):
            self.transport = security._clone()
        else:
            raise TypeError("Need Credential or Transport object")
        self.resource_url = resource_url
        self.cache_time = cache_time
        self._last_properties = None
        self._last_retrieved = datetime.min

    @property
    def properties(self):
        """get resource properties (these are cached for cache_time seconds)"""
        now = datetime.now()
        if (
            self.transport.settings_changed
            or self.cache_time <= 0
            or (timedelta(seconds=self.cache_time) < now - self._last_retrieved)
        ):
            self._last_properties = self.transport.get(url=self.resource_url)
            self._last_retrieved = now
        return self._last_properties

    @property
    def links(self):
        urls = self.properties["_links"]
        return {k: v["href"] for k, v in urls.items()}

    def delete(self):
        """delete/destroy this resource"""
        self.transport.delete(url=self.resource_url)

    def set_properties(self, props):
        """set/update resource properties"""
        return self.transport.put(url=self.resource_url, json=props).json()

    def __repr__(self):
        return f"Resource: {self.resource_url}"

    __str__ = __repr__


class Registry(Resource):
    """Client for a UNICORE service Registry

        >>> base_url = '...' # e.g. "https://localhost:8080/REGISTRY/rest/registries/default_registry"  # noqa
        >>> credential = '...'
        >>> registry = Registry(credential, base_url)

    Will collect the BASE URLs of all registered sites
    """

    def __init__(self, security, url, cache_time=_DEFAULT_CACHE_TIME):
        super().__init__(security, url, cache_time)
        self.refresh()

    def refresh(self):
        self.site_urls = {}
        self.workflow_services_urls = {}

        for entry in self.transport.get(url=self.resource_url)["entries"]:
            # just want the "core" URL and the site ID
            href = entry["href"]
            service_type = entry["type"]
            if "CoreServices" == service_type:
                base = re.match(r"(https://\S+/rest/core).*", href).group(1)
                site_name = re.match(r"https://\S+/(\S+)/rest/core", href).group(1)
                self.site_urls[site_name] = base
            elif "WorkflowServices" == service_type:
                base = re.match(r"(https://\S+/rest/workflows).*", href).group(1)
                site_name = re.match(r"https://\S+/(\S+)/rest/workflows", href).group(1)
                self.workflow_services_urls[site_name] = base

    def site(self, name):
        """Get a client object for the named site"""
        return Client(self.transport, self.site_urls[name])

    def workflow_service(self, name=None):
        """Get a client object for the named site, or the first in the list if no name is given"""
        if name is None:
            _, url = list(self.workflow_services_urls.items())[0]
        else:
            url = self.workflow_services_urls[name]
        return WorkflowService(self.transport, url)


class Client(Resource):
    """Entrypoint to the UNICORE API at a site

    >>> base_url = '...' # e.g. "https://localhost:8080/DEMO-SITE/rest/core"
    >>> credential = credentials.UsernamePassword("demouser", "test123")
    >>> site_client = client.Client(credential, base_url)
    >>> # to get the jobs
    >>> jobs = site_client.get_jobs()
    >>> # to start a new job:
    >>> job_description = {...}
    >>> job = site_client.new_job(job_description)
    """

    def __init__(
        self,
        security,
        site_url,
        check_authentication=True,
        cache_time=_DEFAULT_CACHE_TIME,
    ):
        super().__init__(security, site_url, cache_time)
        if isinstance(self.transport.credential, pyunicore.credentials.Anonymous):
            check_authentication = False
        self.check_authentication = check_authentication
        if self.check_authentication:
            self.assert_authentication()

    def assert_authentication(self):
        '''Asserts that the remote role is not "anonymous"'''
        if self.access_info()["role"]["selected"] == "anonymous":
            raise pyunicore.credentials.AuthenticationFailedException(
                "Failure to authenticate at %s" % self.resource_url
            )

    def access_info(self):
        """get authentication and authentication information about the current user"""
        return self.properties["client"]

    def server_version_info(self):
        """get server version as a tuple (major, minor, patch)"""
        v = self.properties["server"]["version"]
        return tuple([int(x) for x in tuple(v.split("-")[0].split("."))])

    def get_storages(self, offset=0, num=200, tags=[], all=False):
        """get a list of all Storages on this site
        Use the optional 'offset' and 'num' parameters to handle long result lists
        (for long lists, the server might not return all results!).
        Use the optional tag list to filter the results.
        (UNICORE 10): by default, the storage list will not include any job
        directories. Set the 'all' flag to True to also show job directories.
        """
        filter = "all" if all else None
        q_params = _url_params(offset, num, tags, filter)
        urls = self.transport.get(url=self.links["storages"], params=q_params)["storages"]
        return [Storage(self.transport, url) for url in urls]

    def get_transfers(self, offset=0, num=200, tags=[]):
        """get a list of all Transfers.
        Use the optional 'offset' and 'num' parameters to handle long result lists
        (for long lists, the server might not return all results!).
        Use the optional tag list to filter the results."""
        q_params = _url_params(offset, num, tags)
        urls = self.transport.get(url=self.links["transfers"], params=q_params)["transfers"]
        return [Transfer(self.transport, url) for url in urls]

    def get_applications(self):
        apps = []
        for url in self.transport.get(url=self.links["factories"])["factories"]:
            for app in self.transport.get(url=url)["applications"]:
                apps.append(Application(self.transport, url + "/applications/" + app))
        return apps

    def get_compute(self):
        """get a list of all Compute resources"""
        resources = []
        for url in self.transport.get(url=self.links["factories"])["factories"]:
            resources.append(Compute(self.transport, url))
        return resources

    def get_jobs(self, offset=0, num=None, tags=[]):
        """return a list of `Job` objects.
        Use the optional 'offset' and 'num' parameters to handle long result lists
        (for long lists, the server might not return all results!).
        Use the optional tag list to filter the results."""
        q_params = _url_params(offset, num, tags)
        urls = self.transport.get(url=self.links["jobs"], params=q_params)["jobs"]
        return [Job(self.transport, url) for url in urls]

    def new_job(self, job_description, inputs=[], autostart=True):
        """submit and start a job on the site, optionally uploading input data files"""
        if len(inputs) > 0 or job_description.get("haveClientStageIn") is True:
            job_description["haveClientStageIn"] = "true"
        with closing(self.transport.post(url=self.links["jobs"], json=job_description)) as resp:
            job_url = resp.headers["Location"]
        job_type = job_description.get("Job type", "n/a")
        if "ALLOCATE" == job_type.upper():
            job = Allocation(self.transport, job_url)
        else:
            job = Job(self.transport, job_url)
        if len(inputs) > 0:
            working_dir = job.working_dir
            for input_item in inputs:
                working_dir.upload(input_item)
        if autostart and job_description.get("haveClientStageIn", None) == "true":
            job.start()
        return job

    def execute(self, cmd, login_node=None):
        """run a (non-batch) command on the site, executed on a login node
        Args:
            cmd - the command to run
            login_node - optionally specify the login node to run on
        """
        job_description = {"Executable": cmd, "Job type": "INTERACTIVE"}
        if not login_node:
            job_description["Login node"] = login_node
        with closing(self.transport.post(url=self.links["jobs"], json=job_description)) as resp:
            job_url = resp.headers["Location"]

        return Job(self.transport, job_url)

    def issue_auth_token(self, lifetime=-1, renewable=False, limited=False):
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
        with closing(
            self.transport.get(
                url=url, headers={"Accept": "text/plain"}, to_json=False, params=params
            )
        ) as resp:
            return resp.text


class Application(Resource):
    """wrapper around a UNICORE application"""

    def __init__(
        self,
        security,
        app_url,
        submit_url=None,
        cache_time=_DEFAULT_CACHE_TIME,
    ):
        super().__init__(security, app_url, cache_time)
        if submit_url is None:
            submit_url = app_url.split("/rest/core/factories/")[0] + "/rest/core/jobs"
        self.submit_url = submit_url

    @property
    def name(self):
        return self.properties["ApplicationName"]

    @property
    def version(self):
        return self.properties["ApplicationVersion"]

    @property
    def options(self):
        return self.properties["Options"]

    def __repr__(self):
        return "Application {} {} @ {}".format(
            self.name,
            self.version,
            self.submit_url,
        )

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


class Job(Resource):
    """wrapper around UNICORE job"""

    def __init__(self, security, job_url, cache_time=_DEFAULT_CACHE_TIME):
        super().__init__(security, job_url, cache_time)

    @property
    def working_dir(self):
        """return the Storage for accessing this job's working directory"""
        return Storage(self.transport, self.links["workingDirectory"])

    @property
    def status(self):
        return JobStatus(self.properties["status"])

    def bss_details(self):
        """return a JSON containing the low-level batch system details"""
        return self.transport.get(url=self.links["details"])

    def is_running(self):
        """checks whether this job is still running"""
        return self.properties["status"] not in ("SUCCESSFUL", "FAILED")

    def abort(self):
        """abort this job"""
        url = self.links["action:abort"]
        with self.transport.post(url=url, json={}):
            pass

    def restart(self):
        """restart this job"""
        url = self.links["action:restart"]
        with self.transport.post(url=url, json={}):
            pass

    def start(self):
        """start this job - only required if client had to stage-in local files"""
        url = self.links["action:start"]
        with self.transport.post(url=url, json={}):
            pass

    @property
    def job_id(self):
        """get the UUID of this job"""
        return os.path.basename(self.resource_url)

    def poll(self, state=JobStatus.SUCCESSFUL, timeout=0):
        """wait until this job reaches the given status (default : SUCCESSFUL)
        or a later one (like SUCCESSFUL or FAILED).
        If the optional timeout is reached, a TimeoutError will be raised
        Args:
            state - job state to wait for (default : JobStatus.SUCCESSFUL)
            timeout - timeout in seconds (default: 0 = no timeout)
        """
        if state == JobStatus.UNDEFINED:
            raise ValueError("Cannot wait for %s" % state)
        start_time = int(time.time())
        while self.status.ordinal() < state.ordinal():
            wait_time = max(2, self.cache_time + 1)
            time.sleep(wait_time)
            if timeout > 0 and int(time.time()) > start_time + timeout:
                raise TimeoutError("Timeout waiting for job to become %s" % state.value)

    def __repr__(self):
        return "Job: {} submitted: {} running: {}".format(
            self.resource_url,
            self.properties["submissionTime"],
            self.is_running(),
        )

    __str__ = __repr__


class Allocation(Job):
    """A special Job representing a batch system allocation. Tasks can be submitted
    'into' the allocation using the new_job() method. Use 'srun' or whichever
    command is suitable for running the task. UNICORE will automatically set the
    correct job ID, so the task is started in the allocation.
    """

    def __init__(self, security, job_url, cache_time=_DEFAULT_CACHE_TIME):
        super().__init__(security, job_url, cache_time)

    def new_job(self, job_description, inputs=[], autostart=True):
        """submit and start a job within the existing allocation"""
        if len(inputs) > 0 or job_description.get("haveClientStageIn") is True:
            job_description["haveClientStageIn"] = "true"
        with closing(self.transport.post(url=self.resource_url, json=job_description)) as resp:
            job_url = resp.headers["Location"]
        job = Job(self.transport, job_url)
        if len(inputs) > 0:
            working_dir = job.working_dir
            for input_item in inputs:
                working_dir.upload(input_item)
        if autostart and job_description.get("haveClientStageIn", None) == "true":
            job.start()
        return job

    def wait_until_available(self, timeout=0):
        """wait until the allocation is available"""
        self.poll(JobStatus.RUNNING, timeout)
        start_time = int(time.time())
        wait_time = max(2, self.cache_time + 1)
        while True:
            bss_id = self.properties["batchSystemID"]
            if bss_id.startswith("INTERACTIVE_"):
                time.sleep(wait_time)
                if timeout > 0 and int(time.time()) > start_time + timeout:
                    raise TimeoutError("Timeout waiting for allocation to become available")
            else:
                break

    def __repr__(self):
        return "Allocation: {} submitted: {} running: {}".format(
            self.resource_url,
            self.properties["submissionTime"],
            self.is_running(),
        )

    __str__ = __repr__


class Compute(Resource):
    """wrapper around a UNICORE compute resource (a specific cluster with queues)"""

    def __init__(self, security, resource_url, cache_time=_DEFAULT_CACHE_TIME):
        super().__init__(security, resource_url, cache_time)

    def __repr__(self):
        return f"Compute: {self.resource_url}"

    __str__ = __repr__

    def get_queues(self):
        return self.properties["resources"]

    def get_applications(self):
        apps = []
        base_url = self.links["applications"]
        for app in self.properties["applications"]:
            apps.append(Application(self.transport, base_url + "/" + app))
        return apps


class Storage(Resource):
    """wrapper around a UNICORE Storage resource"""

    def __init__(self, security, storage_url, cache_time=_DEFAULT_CACHE_TIME):
        super().__init__(security, storage_url, cache_time)

    def _to_file_url(self, path):
        return (
            self.resource_url
            + "/files"
            + pathlib.Path("/" + path.lstrip("/")).as_posix().rstrip("/")
        )

    def contents(self, path="/"):
        """get a simple list of files in the given directory"""
        return self.transport.get(url=self._to_file_url(path))

    def stat(self, path):
        """get a reference to a file/directory"""
        path_url = self._to_file_url(path)
        headers = {
            "Accept": "application/json",
        }
        props = self.transport.get(url=path_url, headers=headers)
        if props["isDirectory"]:
            ret = PathDir(self, path_url, path)
        else:
            ret = PathFile(self, path_url, path)
        return ret

    def listdir(self, base="/"):
        """get a list of files and directories in the given base directory"""
        ret = {}
        for path, meta in self.contents(base)["content"].items():
            path_url = self._to_file_url(path)
            path = path.lstrip("/")
            if meta["isDirectory"]:
                ret[path] = PathDir(self, path_url, path)
            else:
                ret[path] = PathFile(self, path_url, path)
        return ret

    def rename(self, source, target):
        """rename a file on this storage"""
        json = {
            "from": source,
            "to": target,
        }
        return self.transport.post(url=self.links["action:rename"], json=json)

    def copy(self, source, target):
        """copy a file on this storage"""
        json = {
            "from": source,
            "to": target,
        }
        return self.transport.post(url=self.links["action:copy"], json=json)

    def mkdir(self, name):
        """create a directory"""
        return self.transport.post(url=self._to_file_url(name), json={})

    def rmdir(self, name):
        """remove a directory and all its content"""
        return self.transport.delete(url=self._to_file_url(name))

    def rm(self, name):
        """remove a file"""
        return self.transport.delete(url=self._to_file_url(name))

    def makedirs(self, name):
        """create directory"""
        return self.mkdir(name)

    def upload(self, input_file, destination=None):
        """upload file "input_file" to the remote file "destination".

        Remote directories will be created automatically, if required.
        If "destination" is not given, it is derived from the local
        file path.

        Examples:
        - input_file = "test.txt" -> upload to "test.txt" in the base directory
        of the storage
        - input_file = "/tmp/test.txt" -> upload to "test.txt" in the base directory
        - input_file = "folder1/test.txt" -> upload to "folder1/test.txt",
          automatically creating the "folder1" subdirectory

        Args:
            input_file : the path to the local file
            destination: (optional) the remote file name / path

        """
        if destination is None:
            if os.path.isabs(input_file):
                destination = os.path.basename(input_file)
            else:
                destination = input_file
        _headers = {"Content-Type": "application/octet-stream"}
        with open(input_file, "rb") as fd:
            self.transport.put(url=self._to_file_url(destination), headers=_headers, data=fd)

    def send_file(
        self,
        file_name,
        remote_url,
        protocol=None,
        scheduled=None,
        additional_parameters={},
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
        with closing(self.transport.post(url=dest, json=json)) as resp:
            tr_url = resp.headers["Location"]

        return Transfer(self.transport, tr_url)

    def receive_file(
        self,
        remote_url,
        file_name,
        protocol=None,
        scheduled=None,
        additional_parameters={},
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
        with closing(self.transport.post(url=dest, json=json)) as resp:
            tr_url = resp.headers["Location"]

        return Transfer(self.transport, tr_url)

    def __repr__(self):
        return f"Storage: {self.resource_url}"

    __str__ = __repr__


class Path(Resource):
    """common base for files and directories"""

    def __init__(self, storage, path_url, name, cache_time=_DEFAULT_CACHE_TIME):
        super().__init__(storage.transport, path_url, cache_time)
        self.name = name
        self.storage = storage

    def isdir(self):
        """is a directory"""
        return False

    def isfile(self):
        """is a file"""
        return False

    def get_metadata(self, name=None):
        if name:
            return self.properties["metadata"][name]
        else:
            return self.properties["metadata"]

    def remove(self):
        """remove this file or directory"""
        return self.storage.rm(self.name)

    def __repr__(self):
        return f"{self.__class__.__name__}: {self.name}"

    __str__ = __repr__


class PathDir(Path):
    def __init__(self, storage, path_url, name, cache_time=_DEFAULT_CACHE_TIME):
        super().__init__(storage, path_url, name, cache_time)

    def isdir(self):
        return True

    def __repr__(self):
        return "PathDir: %s" % (self.name)

    __str__ = __repr__


class PathFile(Path):
    def __init__(self, storage, path_url, name, cache_time=_DEFAULT_CACHE_TIME):
        super().__init__(storage, path_url, name, cache_time)

    def download(self, file):
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

        _headers = {"Accept": "application/octet-stream"}
        with closing(
            self.transport.get(
                url=self.resource_url,
                headers=_headers,
                stream=True,
                to_json=False,
            )
        ) as resp:
            chunk_size = 10 * 1024
            if isinstance(file, str):
                with open(file, "wb") as fd:
                    for chunk in resp.iter_content(chunk_size):
                        fd.write(chunk)
            else:
                for chunk in resp.iter_content(chunk_size):
                    file.write(chunk)

    def raw(self, offset=0, size=-1):
        """access the raw http response for streaming purposes.
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

        resp = self.transport.get(
            to_json=False, url=self.resource_url, headers=_headers, stream=True
        )
        return resp.raw

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

    def __init__(self, security, tr_url, cache_time=_DEFAULT_CACHE_TIME):
        super().__init__(security, tr_url, cache_time)

    @property
    def status(self):
        return TransferStatus(self.properties["status"])

    def is_running(self):
        """checks whether this transfer is still running"""
        return self.properties["status"] not in (
            "DONE",
            "FAILED",
        )

    def abort(self):
        """abort this transfer"""
        url = self.properties["_links"]["action:abort"]["href"]
        with self.transport.post(url=url, json={}):
            pass

    def poll(self, state=TransferStatus.DONE, timeout=0):
        """wait until this transfer reaches the given status (default : DONE)
        or a later one (like FAILED or ABORTED).
        If the optional timeout is reached, a TimeoutError will be raised
        Args:
            state - transfer state to wait for (default : TransferStatus.DONE)
            timeout - timeout in seconds (default: 0 = no timeout)
        """
        start_time = int(time.time())
        while self.status.ordinal() < state.ordinal():
            wait_time = max(2, self.cache_time + 1)
            time.sleep(wait_time)
            if timeout > 0 and int(time.time()) > start_time + timeout:
                raise TimeoutError("Timeout waiting for transfer to become %s" % state.value)

    def __repr__(self):
        return "Transfer: {} running: {}".format(
            self.resource_url,
            self.is_running(),
        )

    __str__ = __repr__


class WorkflowService(Resource):
    """Entrypoint for the UNICORE Workflow API

    >>> workflows_url = '...' # e.g. "https://localhost:8080/WORKFLOW/rest/workflows"
    >>> credential = ...
    >>> workflow_service = WorkflowService(credential, workflows_url)
    >>> # to get the list of workflows
    >>> workflows = client.get_workflows()
    >>> # to start a new workflow:
    >>> wf_description = {...}
    >>> wf = workflow_service.new_workflow(wf_description)
    """

    def __init__(
        self,
        security,
        workflows_url,
        check_authentication=True,
        cache_time=_DEFAULT_CACHE_TIME,
    ):
        super().__init__(security, workflows_url, cache_time)
        self.check_authentication = check_authentication
        if self.check_authentication:
            self.assert_authentication()

    def access_info(self):
        """get authentication and authentication information about the current user"""
        return self.properties["client"]

    def assert_authentication(self):
        '''Asserts that the remote role is not "anonymous"'''
        if self.access_info()["role"]["selected"] == "anonymous":
            raise pyunicore.credentials.AuthenticationFailedException(
                "Failure to authenticate at %s" % self.resource_url
            )

    def get_workflows(self, offset=0, num=None, tags=[]):
        """get the list of workflows.

        Use the optional 'offset' and 'num' parameters to handle long result lists
        (for long lists, the server might not return all results!).
        Use the optional tag list to filter the results."""
        q_params = _url_params(offset, num, tags)
        urls = self.transport.get(url=self.resource_url, params=q_params)["workflows"]
        return [Workflow(self.transport, url) for url in urls]

    def new_workflow(self, wf_description):
        """submit a workflow"""
        with closing(self.transport.post(url=self.resource_url, json=wf_description)) as resp:
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

    def __init__(self, security, wf_url, cache_time=_DEFAULT_CACHE_TIME):
        super().__init__(security, wf_url, cache_time)

    @property
    def status(self):
        return WorkflowStatus(self.properties["status"])

    def is_running(self):
        """checks whether this workflow is still running"""
        return self.properties["status"] not in ("SUCCESSFUL", "ABORTED", "FAILED")

    def is_held(self):
        """checks whether this workflow is in HELD state"""
        return self.is_running() and self.properties["status"] == "HELD"

    def poll(self, state=WorkflowStatus.SUCCESSFUL, timeout=0):
        """wait until this workflow reaches the given status (default : SUCCESSFUL)
        or a later one (like FAILED or ABORTED).
        If the optional timeout is reached, a TimeoutError will be raised
        Args:
            state - transfer state to wait for (default : TransferStatus.DONE)
            timeout - timeout in seconds (default: 0 = no timeout)
        """
        start_time = int(time.time())
        while self.status.ordinal() < state.ordinal():
            wait_time = max(2, self.cache_time + 1)
            time.sleep(wait_time)
            if timeout > 0 and int(time.time()) > start_time + timeout:
                raise TimeoutError("Timeout waiting for transfer to become %s" % state.value)

    def abort(self):
        """abort this workflow"""
        url = self.properties["_links"]["action:abort"]["href"]
        with self.transport.post(url=url, json={}):
            pass

    def resume(self, params={}):
        """resume this workflow (from "HELD" state), optionally updating parameters"""
        url = self.properties["_links"]["action:continue"]["href"]
        return self.transport.post(url=url, json=params)

    def get_files(self):
        """get a dictionary of registered workflow files and their
        physical locations
        """
        return self.transport.get(url=self.links["files"])

    def get_jobs(self, offset=0, num=None):
        """return the list of jobs submitted for this workflow
         Use the optional 'offset' and 'num' parameters to handle long result lists
        (for long lists, the server might not return all results!).
        """
        q_params = _url_params(offset, num, [])
        urls = self.transport.get(url=self.links["jobs"], params=q_params)["jobs"]
        return [Job(self.transport, url) for url in urls]

    def stat(self, path):
        """lookup the named workflow file and return a PathFile object"""
        physical_location = self.get_files()[path]
        storage_url, name = physical_location.split("/files/", 1)
        return Storage(self.transport, storage_url).stat(name)

    def __repr__(self):
        return "Workflow: {} submitted: {} running: {}".format(
            self.resource_url,
            self.properties["submissionTime"],
            self.is_running(),
        )

    __str__ = __repr__
