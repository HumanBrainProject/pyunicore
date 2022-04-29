'''
    Client for UNICORE using the REST API

    For full info on the REST API, see https://sourceforge.net/p/unicore/wiki/REST_API/
'''

import os
import re
import requests
import time

from contextlib import closing
from datetime import datetime, timedelta
from jwt import decode as jwt_decode, ExpiredSignatureError

try:
    from urllib3 import disable_warnings
    disable_warnings()
except:
    pass

_REST_CACHE_TIMEOUT = 5  # in seconds
_HBP_REGISTRY_URL = ('https://hbp-unic.fz-juelich.de:7112'
                     '/HBP/rest/registries/default_registry')

_FACTORY_RE = r'''
^                                 # start of line
(?P<site_url>\s*https://.*/       # capture full url
(?P<site_name>.*)                 # capture site name
/rest/core/)
.*                                # ignore the rest
'''

_FACTORY_RE = re.compile(_FACTORY_RE, re.VERBOSE)

_WORKFLOWS_RE = r'''
^                                 # start of line
(?P<site_url>\s*https://.*/       # capture full url
(?P<site_name>.*)                 # capture site name
/rest/workflows)
'''

_WORKFLOWS_RE = re.compile(_WORKFLOWS_RE, re.VERBOSE)


def get_sites(transport, registry_url=_HBP_REGISTRY_URL):
    '''Get all sites from registery'''
    resp = transport.get(url=registry_url)
    site_urls = (prop['href']
                 for prop in resp['entries']
                 if prop['type'] == 'TargetSystemFactory')
    sites = dict(reversed(_FACTORY_RE.match(site).groups())
                 for site in site_urls)
    return sites


def get_workflow_services(transport, registry_url=_HBP_REGISTRY_URL):
    '''Get all workflow services from registery'''
    resp = transport.get(url=registry_url)
    site_urls = (prop['href']
                 for prop in resp['entries']
                 if prop['type'] == 'WorkflowServices')
    sites = dict(reversed(_WORKFLOWS_RE.match(site).groups())
                 for site in site_urls)
    return sites

def _build_full_url(url, offset, num, tags):
    ''' adds optional paging and tags as query to the url '''
    q_params = []
    if offset>0:
        q_params.append("offset=%d" % offset)
    if num is not None:
        q_params.append("num=%d" % num)
    if len(tags)>0:
        q_params.append("tags=" + ','.join(map(str, tags)))
    if len(q_params)>0:
        url = url + "?" + "&".join(map(str, q_params))
    return url

class TimedCacheProperty(object):
    '''decorator to create get only property; values are fetched once per `timeout`'''
    def __init__(self, timeout):
        self._timeout = timedelta(seconds=timeout)
        self._func = None
        self._values = {}

    def __get__(self, instance, cls):
        last_lookup, value = self._values.get(instance, (datetime.min, None))
        now = datetime.now()
        if self._timeout < now - last_lookup:
            value = self._func(instance)
            self._values[instance] = now, value
        return value

    def __call__(self, func):
        self._func = func
        return self


class RefreshHandler(object):
    ''' helper to refresh an OAuth token '''
    def __init__(self, refresh_config, token = None):
        '''
        token: initial access token (can be None)
        refresh_config: a dict containing url, client_id, client_secret, refresh_token
        '''
        self.refresh_config = refresh_config
        self.token = token
        if not token:
            self.refresh()

    def is_valid_token(self):
        '''
        check if the given token is still valid
        TODO check whether token was revoked
        '''
        try:
            jwt_decode(self.token, options={'verify_signature': False,
                                   'verify_nbf': False,
                                   'verify_exp': True,
                                   'verify_aud': False})
            return True
        except ExpiredSignatureError as ex:
            return False

    def refresh(self):
        ''' refresh the token '''
        params = dict(
            client_id=self.refresh_config['client_id'],
            client_secret=self.refresh_config['client_secret'],
            refresh_token=self.refresh_config['refresh_token'],
            grant_type='refresh_token'
        )
        url = "%stoken" % self.refresh_config['url']
        
        res = requests.post(url,headers={"Accept": "application/json"}, data=params)
        res.raise_for_status()
        self.token = res.json()['access_token']
        return self.token
 
    def get_token(self):
        ''' get a valid access token. If necessary, refresh it.
        '''
        if not self.is_valid_token():
            self.refresh()
        return self.token

    
class Transport(object):
    """wrapper around requests, which
           - adds Authorization header (Basic or Bearer style)
           - transparently handles security sessions
           - handles user preferences
           - can be configured with an OIDC refresh handler

       see https://sourceforge.net/p/unicore/wiki/REST_API/#user-preferences
       see https://sourceforge.net/p/unicore/wiki/REST_API/#security-session-handling

       Args:
           auth_token: the value of the auth token
           oidc:       if true, the auth token is a Bearer token, resulting in "Authorization: Bearer <token_value>" header
                       if false, the auth token is a Basic token, resulting in a "Authorization: Basic <auth_token>" header
           refresh_handler: optional refresh handler the will be invoked to refresh the bearer token
           timeout: timeout for HTTP calls (defaults to 120 seconds)
           use_security_sessions: if true, UNICORE's security sessions mechanism will be used (to speed up request processing)
           verify: if true, SSL verification of the server's certificate will be done
    """
    def __init__(self, auth_token, oidc=True, verify=False, refresh_handler=None, use_security_sessions=True, timeout=120):
        super(Transport, self).__init__()
        self.auth_token = auth_token
        self.oidc = oidc
        self.verify = verify
        self.refresh_handler = refresh_handler
        self.use_security_sessions = use_security_sessions
        self.last_session_id = None
        self.preferences = None
        self.timeout = timeout

    def _clone(self):
        ''' create a copy of this transport, with the same initial settings '''
        tr = Transport(self.auth_token, self.oidc, self.verify, self.refresh_handler, self.use_security_sessions, self.timeout)
        tr.last_session_id = self.last_session_id
        tr.preferences = self.preferences
        return tr

    def _headers(self, kwargs):
        if self.oidc:
            if self.refresh_handler:
                try:
                    self.auth_token = self.refresh_handler.get_token()
                except:
                    pass
            val = 'Bearer %s' % self.auth_token
        else:
            val = 'Basic %s' % self.auth_token
        
        headers = {'Authorization': val,
                   'Accept': 'application/json',
                   'Content-Type': 'application/json',
        }
        if self.use_security_sessions and self.last_session_id is not None:
            headers['X-UNICORE-SecuritySession'] = self.last_session_id

        if self.preferences is not None:
            headers['X-UNICORE-User-Preferences'] = self.preferences

        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
            del kwargs['headers']

        return headers

    def checkError(self, res):
        """ checks for error and extracts any error info sent by the server """
        if 400 <= res.status_code < 600:
            reason = res.reason
            try:
                reason = res.json()['errorMessage']
            except:
                pass
            msg =  u'%s Server Error: %s for url: %s' % (res.status_code, reason, res.url)
            raise requests.HTTPError(msg, response=res)
        else:
            res.raise_for_status()

    def repeat_required(self, res, headers):
        if self.use_security_sessions:
            if 432 == res.status_code:
                headers.pop('X-UNICORE-SecuritySession', None)
                return True
        return False
    
    def run_method(self, method, **args):
        ''' performs the requested method, handling security sessions, timeouts etc '''
        headers = self._headers(args)
        res = method(headers=headers, verify=self.verify, timeout=self.timeout, **args)
        if self.repeat_required(res, headers):
            res = method(headers=headers, verify=self.verify, timeout=self.timeout, **args)
        self.checkError(res)
        if self.use_security_sessions:
            self.last_session_id = res.headers.get('X-UNICORE-SecuritySession', None)
        return res;

    def get(self, to_json=True, **kwargs):
        '''do GET and return the response content as JSON

        Note:
            For the raw response, set `to_json` to false
        '''
        res = self.run_method(requests.get, **kwargs)
        if not to_json:
            return res
        json = res.json()
        res.close()
        return json

    def put(self, **kwargs):
        '''do a PUT and return the response '''
        return self.run_method(requests.put, **kwargs)

    def post(self, **kwargs):
        '''do a POST and return the response '''
        return self.run_method(requests.post, **kwargs)

    def delete(self, **kwargs):
        '''send a DELETE to the current endpoint '''
        self.run_method(requests.delete, **kwargs).close()


class Resource(object):
    ''' Base class for a UNICORE resource with properties and some common methods'''

    def __init__(self, transport, resource_url):
        super(Resource, self).__init__()
        self.transport = transport._clone()
        self.resource_url = resource_url

    @TimedCacheProperty(timeout=_REST_CACHE_TIMEOUT)
    def properties(self):
        '''get resource properties (these are cached for 5 seconds)'''
        return self.transport.get(url=self.resource_url)
    
    @property
    def links(self):
        urls = self.transport.get(url=self.resource_url)['_links']
        return {k: v['href'] for k, v in urls.items()}

    def delete(self):
        '''delete/destroy this resource'''
        self.transport.delete(url=self.resource_url)

    def set_properties(self, props):
        '''set/update resource properties'''
        return self.transport.put(url=self.resource_url, json=props).json()

    def __repr__(self):
        return ('Resource: %s' %
                (self.resource_url,
                ))

    __str__ = __repr__

class Registry(Resource):
    ''' Client for a UNICORE service Registry 

        >>> base_url = '...' # e.g. "https://localhost:8080/REGISTRY/rest/registries/default_registry"
        >>> token = '...'
        >>> transport = Transport(token)
        >>> registry = Registry(transport, base_url)

    Will collect the BASE URLs of all registered sites
    '''

    def __init__(self, transport, url):
        super(Registry, self).__init__(transport,url)
        self.refresh()
    
    def refresh(self):
        self.site_urls = {}
        self.workflow_services_urls = {}

        for entry in self.transport.get(url=self.resource_url)['entries']:
            try:
                # just want the "core" URL and the site ID
                href = entry['href']
                service_type = entry['type']
                if "TargetSystemFactory" == service_type:
                    base = re.match(r"(https://\S+/rest/core).*", href).group(1)
                    site_name = re.match(r"https://\S+/(\S+)/rest/core", href).group(1)
                    self.site_urls[site_name]=base
                elif "WorkflowServices" == service_type:
                    base = re.match(r"(https://\S+/rest/workflows).*", href).group(1)
                    site_name = re.match(r"https://\S+/(\S+)/rest/workflows", href).group(1)
                    self.workflow_services_urls[site_name]=base

            except Exception as e:
                print(e)

    def site(self, name):
        ''' Get a client object for the named site '''
        url = self.site_urls[name]
        return Client(self.transport, url)

    def workflow_service(self, name=None):
        ''' Get a client object for the named site, or the first in the list if no name is given '''
        if name is None:
            _, url = list(self.workflow_services_urls.items())[0]
        else:
            url = self.workflow_services_urls[name]
        return WorkflowService(self.transport, url)


class Client(object):
    '''Entrypoint to the UNICORE API at a site

        >>> base_url = '...' # e.g. "https://localhost:8080/DEMO-SITE/rest/core"
        >>> token = '...'
        >>> transport = Transport(token)
        >>> sites = get_sites(transport)
        >>> client = Client(transport, sites['JURECA'])
        >>> # to get the jobs
        >>> jobs = client.get_jobs()
        >>> # to start a new job:
        >>> job_description = {...}
        >>> job = client.new_job(job_description)
    '''
    
    def __init__(self, transport, site_url, check_authentication=True):
        super(Client, self).__init__()
        self.transport = transport
        self.site_url = site_url
        self.check_authentication = check_authentication
        if self.check_authentication:
            self.assert_authentication()

    @TimedCacheProperty(timeout=_REST_CACHE_TIMEOUT)
    def properties(self):
        return self.transport.get(url=self.site_url)

    @property
    def links(self):
        urls = self.transport.get(url=self.site_url)['_links']
        return {k: v['href'] for k, v in urls.items()}

    def assert_authentication(self):
        ''' Asserts that the remote role is not "anonymous" '''
        if self.access_info()['role']['selected']=="anonymous":
            raise Exception("Failure to authenticate at %s" % self.site_url)
        
    def access_info(self):
        '''get authentication and authorization information about the current user'''
        return self.properties['client']

    def get_storages(self, offset=0, num=200, tags=[]):
        '''get a list of all Storages on this site
        Use the optional 'offset' and 'num' parameters to handle long result lists
        (for long lists, the server might not return all results!).
        Use the optional tag list to filter the results.'''
        s_url = _build_full_url(self.links['storages'], offset, num, tags)
        return [Storage(self.transport, url)
                for url in self.transport.get(url=s_url)['storages']]

    def get_transfers(self, offset=0, num=200, tags=[]):
        '''get a list of all Transfers.
        Use the optional 'offset' and 'num' parameters to handle long result lists
        (for long lists, the server might not return all results!).
        Use the optional tag list to filter the results.'''
        t_url = _build_full_url(self.links['transfers'], offset, num, tags)
        return [Transfer(self.transport, url)
                for url in self.transport.get(url=t_url)['transfers']]

    def get_applications(self):
        apps = []
        for url in self.transport.get(url=self.links['factories'])['factories']:
            for app in self.transport.get(url=url)['applications']:
                apps.append(Application(self.transport, url+"/applications/"+app))
        return apps

    def get_compute(self):
        '''get a list of all Compute resources'''
        resources = []
        for url in self.transport.get(url=self.links['factories'])['factories']:
            resources.append(Compute(self.transport, url))
        return resources

    def get_jobs(self, offset=0, num=None, tags=[]):
        '''return a list of `Job` objects.
        Use the optional 'offset' and 'num' parameters to handle long result lists
        (for long lists, the server might not return all results!).
        Use the optional tag list to filter the results.'''
        j_url = _build_full_url(self.links['jobs'], offset, num, tags)
        return [Job(self.transport, url)
                for url in self.transport.get(url=j_url)['jobs']]

    def new_job(self, job_description, inputs=[], autostart = True):
        ''' submit and start a job on the site, optionally uploading input data files '''
        if len(inputs)>0 or job_description.get('haveClientStageIn') is True :
            job_description['haveClientStageIn'] = "true"

        with closing(self.transport.post(url=self.links['jobs'], json=job_description)) as resp:
            job_url = resp.headers['Location']
        
        job = Job(self.transport, job_url)

        if len(inputs)>0:
            working_dir = job.working_dir
            for input_item in inputs:
                working_dir.upload(input_item)
        if autostart and job_description.get('haveClientStageIn', None) == "true":
            try:
                job.start()
            except:
                pass

        return job


    def execute(self, cmd):
        ''' run a (non-batch) command on the site, executed on a login node '''
        job_description = {'Executable': cmd,
                           'Job type': 'INTERACTIVE'
        }
        with closing(self.transport.post(url=self.links['jobs'], json=job_description)) as resp:
            job_url = resp.headers['Location']
        
        return Job(self.transport, job_url)


class Application(Resource):
    '''wrapper around a UNICORE application '''
    def __init__(self, transport, app_url, submit_url=None):
        super(Application, self).__init__(transport, app_url)
        if submit_url is None:
            submit_url = app_url.split("/rest/core/factories/")[0]+"/rest/core/jobs"
        self.submit_url = submit_url

    @TimedCacheProperty(timeout=3600)
    def name(self):
        return self.properties['ApplicationName']

    @TimedCacheProperty(timeout=3600)
    def version(self):
        return self.properties['ApplicationVersion']

    @TimedCacheProperty(timeout=3600)
    def options(self):
        return self.properties['Options']

    def __repr__(self):
        return ('Application %s %s @ %s' %
                 (self.name,
                  self.version,
                  self.submit_url))

    __str__ = __repr__



class Job(Resource):
    '''wrapper around UNICORE job'''

    def __init__(self, transport, job_url):
        super(Job, self).__init__(transport, job_url)

    @property
    def working_dir(self):
        '''return the Storage for accessing the working directory '''
        return Storage(
            self.transport,
            self.links['workingDirectory'])

    def bss_details(self):
        ''' return a JSON containing the low-level batch system details '''
        return self.transport.get(url=self.links['details'])

    def is_running(self):
        '''checks whether a job is still running'''
        status = self.properties['status']
        return status not in ('SUCCESSFUL', 'FAILED', )

    def abort(self):
        '''abort the job'''
        url = self.links['action:abort']
        return self.transport.post(url=url, json={})

    def restart(self):
        '''restart the job'''
        url = self.links['action:restart']
        return self.transport.post(url=url, json={})

    def start(self):
        '''start the job - only required if client had to stage-in local files '''
        url = self.links['action:start']
        return self.transport.post(url=url, json={})

    @property
    def job_id(self):
        '''get the UID of the job'''
        return os.path.basename(self.resource_url)

    def poll(self):
        '''wait until job completes'''
        while self.is_running():
            time.sleep(_REST_CACHE_TIMEOUT + 0.1)

    def __repr__(self):
        return ('Job: %s submitted: %s running: %s' %
                (self.resource_url,
                 self.properties['submissionTime'],
                 self.is_running()))

    __str__ = __repr__

class Compute(Resource):
    ''' wrapper around a UNICORE compute resource (a specific cluster with queues) '''
    def __init__(self, transport, job_url):
        super(Compute, self).__init__(transport, job_url)

    def __repr__(self):
        return ('Compute: %s' %
                (self.resource_url,
                ))

    __str__ = __repr__
    
    def get_queues(self):
        return self.properties['resources']

    def get_applications(self):
        apps = []
        base_url = self.links['applications']
        for app in self.properties['applications']:
            apps.append(Application(self.transport, base_url+"/"+app))
        return apps

class Storage(Resource):
    ''' wrapper around a UNICORE Storage resource '''

    def __init__(self, transport, storage_url):
        super(Storage, self).__init__(transport, storage_url)
        self.storage_url = storage_url

    def files_url(self):
        return self.links['files']+'/'

    def contents(self, path="/"):
        '''get a simple list of files in the given directory '''
        return self.transport.get(url=self.links['files']+'/'+path)

    def stat(self, path):
        ''' get a reference to a file/directory '''
        path_url = self.links['files'] + '/' + path
        headers = {'Accept': 'application/json',}
        props = self.transport.get(url=path_url, headers = headers)
        if props['isDirectory']:
            ret = PathDir(self, path_url, path)
        else:
            ret = PathFile(self, path_url, path)
        return ret
    
    def listdir(self, base='/'):
        ''' get a list of files and directories in the given base directory '''
        ret = {}
        for path, meta in self.contents(base)['content'].items():
            path_url = self.links['files'] + path
            path = path[1:]  # strip leading '/'
            if meta['isDirectory']:
                ret[path] = PathDir(self, path_url, path)
            else:
                ret[path] = PathFile(self, path_url, path)
        return ret

    def rename(self, source, target):
        '''rename a file on this storage'''
        json = {'from': source,
                'to': target,
                }
        return self.transport.post(url=self.links['action:rename'], json=json)

    def copy(self, source, target):
        '''copy a file on this storage'''
        json = {'from': source,
                'to': target,
                }
        return self.transport.post(url=self.links['action:copy'], json=json)

    def mkdir(self, name):
        '''create a directory'''
        return self.transport.post(url=self.links['files']+"/"+name, json={})

    def rmdir(self, name):
        '''remove a directory and all its content'''
        return self.transport.delete(url=self.links['files']+"/"+name)

    def rm(self, name):
        '''remove a file'''
        return self.transport.delete(url=self.links['files']+"/"+name)

    def makedirs(self, name):
        '''create directory'''
        return self.mkdir(name)

    def upload(self, input_file, destination=None):
        """ upload file "input_file" to the remote file "destination".

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
        headers = {'Content-Type': 'application/octet-stream'}
        with open(input_file, 'rb') as fd:
            self.transport.put(
                url=os.path.join(self.resource_url, "files", destination),
                headers=headers,
                data=fd)

    def send_file(self, file_name, remote_url, protocol=None, scheduled=None, additional_parameters={}):
        """ launch a server-to-server transfer: send a file from this storage to a remote location 

        Args:
            file_name : the file on this storage to send (supports wildcards)
            remote_url: the destination (https://.../rest/core/storages/NAME/files/path_to_file_or_directory
            protocol: optional protocol (e.g. "UFTP")
            additional_parameters: any protocol-dependent additional settings

        Returns:
            a Transfer object
        """
        params = additional_parameters.copy()
        if protocol:
            remote_url = protocol+":"+remote_url
        if scheduled:
            params['scheduledStartTime'] = scheduled
        json = {
            "file": file_name,
            "target": remote_url,
            "extraParameters": params
        }
        dest = self.links.get('transfers', self.storage_url+"/transfers")
        with closing(self.transport.post(url=dest, json=json)) as resp:
            tr_url = resp.headers['Location']
        
        return Transfer(self.transport, tr_url)

    def receive_file(self, remote_url, file_name, protocol=None, scheduled=None, additional_parameters={}):
        """ launch a server-to-server transfer: pull a file from a remote storage to this storage

        Args:
            remote_url: the remote file (supports wildcards) (https://.../rest/core/storages/NAME/files/path_to_file
            file_name : the file on this storage to write to
            protocol: optional protocol (e.g. "UFTP")
            additional_parameters: any protocol-dependent additional settings

        Returns:
            a Transfer object
        """
        params = additional_parameters.copy()
        if protocol:
            remote_url = protocol+":"+remote_url
        if scheduled:
            params['scheduledStartTime'] = scheduled
        json = {
            "file": file_name,
            "source": remote_url,
            "extraParameters": params
        }

        dest = self.links.get('transfers', self.storage_url+"/transfers")
        with closing(self.transport.post(url=dest, json=json)) as resp:
            tr_url = resp.headers['Location']
        
        return Transfer(self.transport, tr_url)

    def __repr__(self):
        return ('Storage: %s' %
                (self.storage_url,
                ))

    __str__ = __repr__


class Path(Resource):
    ''' common base for files and directories '''

    def __init__(self, storage, path_url, name):
        super(Path, self).__init__(storage.transport, path_url)
        self.name = name
        self.storage = storage

    def isdir(self):
        '''is a directory'''
        return False

    def isfile(self):
        '''is a file'''
        return False

    def get_metadata(self, name=None):
        if name:
            return self.properties['metadata'][name]
        else:
            return self.properties['metadata']

    def remove(self):
        '''remove this file or directory'''
        return self.storage.rm(self.name)

    def __repr__(self):
        return '%s: %s' % (self.__class__.__name__, self.name)

    __str__ = __repr__


class PathDir(Path):
    def __init__(self, storage, path_url, name):
        super(PathDir, self).__init__(storage, path_url, name)

    def isdir(self):
        return True

    def __repr__(self):
        return 'PathDir: %s' % (self.name)

    __str__ = __repr__


class PathFile(Path):
    def __init__(self, storage, path_url, name):
        super(PathFile, self).__init__(storage, path_url, name)

    def download(self, file_):
        '''download file

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
        '''

        hdr = {'Accept': 'application/octet-stream'}
        with closing(
            self.transport.get(url=self.resource_url,
                               headers=hdr,
                               stream=True,
                               to_json=False,
                               )) as resp:
           
            CHUNK_SIZE = 10 * 1024
            if isinstance(file_, str):
                with open(file_, 'wb') as fd:
                    for chunk in resp.iter_content(CHUNK_SIZE):
                        fd.write(chunk)
            else:
                for chunk in resp.iter_content(CHUNK_SIZE):
                    file_.write(chunk)

    def raw(self, offset=0, size=-1):
        ''' access the raw http response for streaming purposes. 
            The optional 'offset' and 'size' parameters allow to download only
            part of the file.
            NOTE: this is the raw response from the server and might not be 
                  decoded appropriately!
        '''
        headers = {'Accept': 'application/octet-stream'}
        if offset<0:
            raise ValueError("Offset must be positive")
        if offset>0 or size>-1:
            range = "bytes=%s-" % offset
            if size>-1:
                range += str(size+offset-1)
            headers['Range']=range

        resp = self.transport.get(to_json=False, url=self.resource_url, headers=headers, stream=True)
        return resp.raw

    def isfile(self):
        return True

class Transfer(Resource):
    '''wrapper around a UNICORE server-to-server transfer'''

    def __init__(self, transport, tr_url):
        super(Transfer, self).__init__(transport, tr_url)

    def is_running(self):
        '''checks whether a workflow is still running'''
        status = self.properties['status']
        return status not in ('DONE', 'FAILED', )

    def abort(self):
        '''abort the workflow'''
        url = self.properties['_links']['action:abort']['href']
        return self.transport.post(url=url, json={})

    def __repr__(self):
        return ('Transfer: %s running: %s' %
                 (self.resource_url,
                 self.is_running()))

    __str__ = __repr__



class WorkflowService(object):
    '''Entrypoint for the UNICORE Workflow API

        >>> workflows_url = '...' # e.g. "https://localhost:8080/WORKFLOW/rest/workflows"
        >>> token = '...'
        >>> transport = Transport(token)
        >>> workflow_service = Client(transport, workflows_url)
        >>> # to get the list of workflows
        >>> workflows = client.get_workflows()
        >>> # to start a new workflow:
        >>> wf_description = {...}
        >>> wf = workflow_service.new_workflow(wf_description)
    '''
    
    def __init__(self, transport, workflows_url, check_authentication=True):
        super(WorkflowService, self).__init__()
        self.transport = transport
        self.workflows_url = workflows_url
        self.check_authentication = check_authentication
        if self.check_authentication:
            self.assert_authentication()
            
    @TimedCacheProperty(timeout=_REST_CACHE_TIMEOUT)
    def properties(self):
        return self.transport.get(url=self.workflows_url)

    def access_info(self):
        '''get authentication and authorization information about the current user'''
        return self.properties['client']

    def assert_authentication(self):
        ''' Asserts that the remote role is not "anonymous" '''
        if self.access_info()['role']['selected']=="anonymous":
            raise Exception("Failure to authenticate at %s" % self.workflows_url)

    def get_workflows(self, offset=0, num=None, tags=[]):
        ''' get the list of workflows.

        Use the optional 'offset' and 'num' parameters to handle long result lists
        (for long lists, the server might not return all results!).
        Use the optional tag list to filter the results.'''
        w_url = _build_full_url(self.workflows_url, offset, num, tags)
        return [Workflow(self.transport, url)
                for url in self.transport.get(url=w_url)['workflows']]

    def new_workflow(self, wf_description):
        ''' submit a workflow '''
        with closing(self.transport.post(url=self.workflows_url, json=wf_description)) as resp:
            wf_url = resp.headers['Location']
        return Workflow(self.transport, wf_url)


class Workflow(Resource):
    '''wrapper around a UNICORE workflow'''

    def __init__(self, transport, wf_url):
        super(Workflow, self).__init__(transport, wf_url)

    def is_running(self):
        '''checks whether a workflow is still running'''
        status = self.properties['status']
        return status not in ('SUCCESSFUL', 'FAILED', )

    def abort(self):
        '''abort the workflow'''
        url = self.properties['_links']['action:abort']['href']
        return self.transport.post(url=url, json={})

    def resume(self, params={}):
        '''resume a held workflow, optionally updating parameters'''
        url = self.properties['_links']['action:resume']['href']
        return self.transport.post(url=url, json={})

    def get_files(self):
        ''' get a dictionary of registered workflow files and their 
            physical locations
        '''
        return self.transport.get(url=self.links['files'])

    def get_jobs(self, offset=0, num=None):
        '''return the list of jobs submitted for this workflow
         Use the optional 'offset' and 'num' parameters to handle long result lists
        (for long lists, the server might not return all results!).
         '''
        j_url = _build_full_url(self.links['jobs'], offset, num, [])
        return [Job(self.transport, url)
                for url in self.transport.get(url=j_url)['jobs']]

    def stat(self, path):
        ''' lookup the named workflow file and return a PathFile object '''
        physical_location = self.get_files()[path]
        storage_url, name = physical_location.split("/files/",1)
        return Storage(self.transport, storage_url).stat(name)

    def __repr__(self):
        return ('Workflow: %s submitted: %s running: %s' %
                 (self.resource_url,
                 self.properties['submissionTime'],
                 self.is_running()))

    __str__ = __repr__

