''' Client for UNICORE 
    Based on https://sourceforge.net/p/unicore/wiki/REST_API/
'''

import cStringIO
import logging
import os
import re
import requests
import time
import sys
from contextlib import closing
from datetime import datetime, timedelta

if sys.version_info < (3, 0):
    from types import StringType
else:
    StringType = str  # pragma: no cover

# TODO:
# - Add Application discovery and launch creation
#   >>> BSP = client.get_application('BSP')
#   >>> BSP('foo', 'bar', 'baz')  # to launch it

# - Turn off verify=False once certificates are correct

L = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings()
REST_CACHE_TIMEOUT = 5  # in seconds
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


class TimedCache(object):
    '''decorator so that calls are only made once per `timeout`'''
    def __init__(self, timeout):
        self._timeout = timedelta(seconds=timeout)
        self._last_lookup = datetime.min
        self._value = None

    def __call__(self, func):
        def wrap(*args, **kwargs):
            now = datetime.now()
            if self._timeout < now - self._last_lookup:
                self._last_lookup = now
                self._value = func(*args, **kwargs)
            return self._value
        return wrap

def get_sites(transport, registry_url=_HBP_REGISTRY_URL):
    '''Get all sites from registery'''
    resp = transport.get(url=registry_url)
    site_urls = (prop['href']
                 for prop in resp['entries']
                 if prop['type'] == 'TargetSystemFactory')
    sites = dict(reversed(_FACTORY_RE.match(site).groups())
                 for site in site_urls)
    return sites


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


class Transport(object):
    '''wrapper around requests to add authentication headers'''
    def __init__(self, auth_token, oidc=True, verify=False):
        super(Transport, self).__init__()
        self.auth_token = auth_token
        self.oidc = oidc
        # TODO: should default to True once certificates are correct
        self.verify = verify

    def _headers(self, kwargs):
        if self.oidc:
            val = 'Bearer %s' % self.auth_token
        else:
            val = 'Basic %s' % self.auth_token
        
        headers = {'Authorization': val,
                   'Accept': 'application/json',
                   }

        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
            del kwargs['headers']

        return headers

    def get(self, to_json=True, **kwargs):
        '''do get

        Note:
            For the complete response, set `to_json` to false
        '''
        headers = self._headers(kwargs)
        req = requests.get(headers=headers, verify=self.verify, **kwargs)
        req.raise_for_status()
        if not to_json:
            return req
        return req.json()

    def put(self, **kwargs):
        headers = self._headers(kwargs)
        req = requests.put(headers=headers, verify=self.verify, **kwargs)
        req.raise_for_status()
        return req

    def post(self, **kwargs):
        headers = self._headers(kwargs)
        req = requests.post(headers=headers, verify=self.verify, **kwargs)
        req.raise_for_status()
        return req

    def delete(self, **kwargs):
        headers = self._headers(kwargs)
        req = requests.delete(headers=headers, verify=self.verify, **kwargs)
        req.raise_for_status()


class Resource(object):
    ''' Base class for a UNICORE resource with properties and some common methods'''

    def __init__(self, transport, resource_url):
        super(Resource, self).__init__()
        self.transport = transport
        self.resource_url = resource_url

    @property
    @TimedCache(timeout=REST_CACHE_TIMEOUT)
    def properties(self):
        return self.transport.get(url=self.resource_url)

    def delete(self):
        self.transport.delete(url=self.resource_url)


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
        for entry in self.transport.get(url=self.resource_url)['entries']:
            try:
                # just want the "core" URL and the site ID
                href = entry['href']
                service_type = entry['type']
                if "TargetSystemFactory" == service_type:
                    base = re.match(r"(https://\S+/rest/core).*", href).group(1)
                    site_name = re.match(r"https://\S+/(\S+)/rest/core", href).group(1)
                    self.site_urls[site_name]=base
            except Exception as e:
                print(e)

    def site(self, name):
        ''' Get a client object for the named site '''
        url = self.site_urls[name]
        return Client(self.transport, url)


class Client(object):
    '''Entrypoint to UNICORE API at a site

        >>> base_url = '...' # e.g. "https://localhost:8080/DEMO-SITE/rest/core"
        >>> token = '...'
        >>> transport = Transport(token)
        >>> client = Client(transport, base_url)
        >>> # to get the jobs
        >>> client.get_jobs()
        >>> # to start a new job:
        >>> job_description = {...}
        >>> job = client.new_job(job_description)

    '''
    
    def __init__(self, transport, site_url):
        super(Client, self).__init__()
        self.transport = transport
        self.site_url = site_url
        self.site_urls = {
            k: v['href']
            for k, v in self.transport.get(url=site_url)['_links'].items()}

    @property
    @TimedCache(timeout=REST_CACHE_TIMEOUT)
    def properties(self):
        return self.transport.get(url=self.site_url)

    def access_info(self):
        return self.properties['client']

    def get_storages(self):
        return [PathDir(self.transport, url, '/')
                for url in self.transport.get(url=self.site_urls['storages'])['storages']]

    def get_applications(self):
        apps = []
        for url in self.transport.get(url=self.site_urls['factories']):
            for app in self.transport.get(url=url)['applications']:
                app += Application(self.transport, app)

    def get_jobs(self):
        return [Job(self.transport, url)
                for url in self.transport.get(url=self.site_urls['jobs'])['jobs']]

    def new_job(self, job_description):
        ''' run a batch job on the site '''
        resp = self.transport.post(url=self.site_urls['jobs'],
                                   json=job_description)
        job_url = resp.headers['Location']
        return Job(self.transport, job_url)

    def execute(self, cmd):
        ''' run a (non-batch) command on the site '''
        job_description = {'Executable': cmd,
                           'Environment': {'UC_PREFER_INTERACTIVE_EXECUTION':'true'},
        }
        resp = self.transport.post(url=self.site_urls['jobs'],
                                   json=job_description)
        job_url = resp.headers['Location']
        return Job(self.transport, job_url)


class Application(object):
    '''wrapper around a UNICORE application '''
    def __init__(self, name, version=None):
        self.name = name
        self.version = version


class Job(Resource):
    '''wrapper around UNICORE job'''
    def __init__(self, transport, job_url):
        super(Job, self).__init__(transport, job_url)

    @property
    def working_dir(self):
        '''return the working directory'''
        return PathDir(
            self.transport,
            self.properties['_links']['workingDirectory']['href'],
            '/')

    def is_running(self):
        '''checks whether a job is still running'''
        status = self.properties['status']
        return status not in ('SUCCESSFUL', 'FAILED', )

    def abort(self):
        '''abort the job'''
        url = self.properties['_links']['action:abort']['href']
        return self.transport.post(url=url, json={})

    def restart(self):
        '''restart the job'''
        url = self.properties['_links']['action:restart']['href']
        return self.transport.post(url=url, json={})

    def start(self):
        '''start the job - only required if client had to stage-in local files '''
        url = self.properties['_links']['action:start']['href']
        return self.transport.post(url=url, json={})

    @property
    def job_id(self):
        '''get the UID of the job'''
        return os.path.basename(self.resource_url)

    def poll(self):
        '''wait until job completes'''
        while self.properties['status'] in ('QUEUED', 'RUNNING'):
            L.debug('Sleeping %s', REST_CACHE_TIMEOUT + 0.1)
            time.sleep(REST_CACHE_TIMEOUT + 0.1)

    def __repr__(self):
        return ('Job: %s: %s, submitted: %s running: %s' %
                (self.job_id,
                 os.path.basename(self.properties['_links']['self']['href']),
                 self.properties['submissionTime'],
                 self.is_running()))

    __str__ = __repr__


class Path(Resource):
    ''' common base for files and directories '''

    def __init__(self, transport, path_url, name):
        super(Path, self).__init__(transport, path_url)
        self.name = name

    @property
    def path_urls(self):
        urls = self.transport.get(url=self.resource_url)['_links']
        return {k: v['href'] for k, v in urls.items()}

    def isdir(self):
        '''is a directory'''
        return False

    def isfile(self):
        '''is a file'''
        return False

    #def get_metadata(self, name):
    #    pass
    
    def remove(self):
        '''remove file or directory'''
        return self.transport.delete(url=self.path_urls['files']+"/"+name)


class PathDir(Path):
    def __init__(self, transport, path_url, name):
        super(PathDir, self).__init__(transport, path_url, name)
        self._last_contents_lookup = datetime.min
        self._cached_contents = {}

    def __repr__(self):
        return '%s: %s' % (self.__class__.__name__, self.name)

    __str__ = __repr__

    @property
    @TimedCache(timeout=REST_CACHE_TIMEOUT)
    def contents(self):
        return self.transport.get(url=self.path_urls['files'])

    def upload(self, input_name, destination=None):
        '''upload path `input_name` to the directory, optionally renaming it to "destination" '''
        assert self.isdir(), 'Not a directory'
        if destination is None:
            destination = os.path.basename(input_name)
        
        headers = {'Content-Type': 'application/octet-stream',
                   }
        with open(input_name, 'rb') as fd:
            resp = self.transport.put(
                url=os.path.join(self.resource_url, 'files', destination),
                headers=headers,
                data=fd)

    def download(self, remote_file, destination=None):
        ''' download remote_file to the current directory, optionally to the given local destination '''
        
        assert self.isdir(), 'Not a directory'
        headers = {'Accept': 'application/octet-stream',}
        url = os.path.join(self.resource_url, 'files', remote_file)
        if destination is None:
            destination = os.path.basename(remote_file)
        resp = self.transport.get(to_json=False, url=url, headers=headers, stream=True)
        resp.raise_for_status()
        with open(destination, 'wb') as fd:
            for chunk in resp.iter_content(chunk_size=512):
                fd.write(chunk)

    def listdir(self):
        '''list the contents of the directory'''
        ret = {}
        for path, meta in self.contents['content'].items():
            path_url = self.path_urls['files'] + path
            path = path[1:]  # strip leading '/'
            if meta['isDirectory']:
                ret[path] = PathDir(self.transport, path_url, path)
            else:
                ret[path] = PathFile(self.transport, path_url, path)
        return ret

    def isdir(self):
        return True

    def rename(self, source, target):
        '''rename file in directory'''
        json = {'from': source,
                'to': target,
                }
        return self.transport.post(url=self.path_urls['rename'], json=json)

    def copy(self, source, target):
        '''rename file in directory'''
        json = {'from': source,
                'to': target,
                }
        return self.transport.post(url=self.path_urls['copy'], json=json)

    def mkdir(self, name):
        return self.transport.post(url=self.path_urls['files']+"/"+name, json={})

    def rmdir(self, name):
        return self.transport.delete(url=self.path_urls['files']+"/"+name)

    def makedirs(self, name):
        return self.mkdir(name)

    def __repr__(self):
        return 'Storage: %s' % (self.resource_url)

    __str__ = __repr__


class PathFile(Path):
    def __init__(self, transport, path_url, name):
        super(PathFile, self).__init__(transport, path_url, name)

    def download(self, file_, max_size=10**6):
        '''download file

        Args:
            file_(StringType or file-like): if a string, a file of that name
            will be created, and filled with the download.  If it's a file-like,
            then the contents will be write()

            max_size(int): if the file is larger than this, the file won't be
            downloaded (only relevant if the target is file like)

            You can also use the raw() method for data streaming purposes

            >>> import cStringIO
            >>> foo = wd.listdir()['foo.txt']
            >>> foo_contents = cStringIO.StringIO()
            >>> foo.download(foo_contents)
            >>> print(foo.contents.getvalue())
        '''

        with closing(
            self.transport.get(url=self.resource_url,
                               headers={'Accept': 'application/octet-stream'},
                               stream=True,
                               to_json=False,
                               )) as resp:
            resp.raise_for_status()
            if max_size < int(resp.headers['content-length']):
                raise Exception('File too long')

            CHUNK_SIZE = 10 * 1024
            if isinstance(file_, StringType):
                with open(file_, 'wb') as fd:
                    for chunk in resp.iter_content(CHUNK_SIZE):
                        fd.write(chunk)
            else:
                for chunk in resp.iter_content(CHUNK_SIZE):
                    file_.write(chunk)

    def raw(self):
        ''' access the raw http response for streaming purposes '''
        headers = {'Accept': 'application/octet-stream',}
        resp = self.transport.get(to_json=False, url=self.resource_url, headers=headers, stream=True)
        resp.raise_for_status()
        return resp.raw

    def isfile(self):
        return True
