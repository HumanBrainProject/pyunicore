''' Client for UNICORE '''

import cStringIO
import logging
import os
from re import match
import time

from contextlib import closing
from datetime import datetime, timedelta

import requests

L = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings()
REST_CACHE_TIMEOUT = 5  # in seconds


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


class Transport(object):
    '''wrapper around requests to add authentication headers'''
    def __init__(self, auth_token, oidc=True):
        super(Transport, self).__init__()
        self.auth_token = auth_token
        self.oidc = oidc

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
        headers = self._headers(kwargs)
        req = requests.get(headers=headers, verify=False, **kwargs)
        req.raise_for_status()
        if not to_json:
            return req
        return req.json()

    def put(self, **kwargs):
        headers = self._headers(kwargs)
        req = requests.put(headers=headers, verify=False, **kwargs)
        req.raise_for_status()
        return req

    def post(self, **kwargs):
        headers = self._headers(kwargs)
        req = requests.post(headers=headers, verify=False, **kwargs)
        req.raise_for_status()
        return req

    def delete(self, **kwargs):
        headers = self._headers(kwargs)
        req = requests.delete(headers=headers, verify=False, **kwargs)
        req.raise_for_status()


class Registry(object):
    ''' Client for a UNICORE service Registry 

        >>> base_url = '...' # e.g. "https://localhost:8080/REGISTRY/rest/registries/default_registry"
        >>> token = '...'
        >>> transport = Transport(token)
        >>> registry = Registry(transport, base_url)

    Will collect the BASE URLs of all registered sites
    '''

    def __init__(self, transport, site_url):
        super(Registry, self).__init__()
        self.transport = transport
        self.site_url = site_url
        self.refresh()

    @property
    @TimedCache(timeout=REST_CACHE_TIMEOUT)
    def properties(self):
        return self.transport.get(url=self.site_url)
    
    def refresh(self):
        self.site_urls = {}
        for entry in self.transport.get(url=self.site_url)['entries']:
            try:
                # just want the "core" URL and the site ID
                href = entry['href']
                service_type = entry['type']
                if "TargetSystemFactory" == service_type:
                    base = match(r"(https://\S+/rest/core).*", href).group(1)
                    site_name = match(r"https://\S+/(\S+)/rest/core", href).group(1)
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


class Site(object):
    '''wrapper around a UNICORE site '''
    def __init__(self, transport, site_url):
        super(Site, self).__init__()
        self.transport = transport
        self.site_url = site_url

    @property
    @TimedCache(timeout=REST_CACHE_TIMEOUT)
    def properties(self):
        return self.transport.get(url=self.site_url)

class Application(object):
    '''wrapper around a UNICORE site '''
    def __init__(self, transport, site_url):
        super(Site, self).__init__()
        self.transport = transport
        self.site_url = site_url

    @property
    @TimedCache(timeout=REST_CACHE_TIMEOUT)
    def properties(self):
        return self.transport.get(url=self.site_url)


class Job(object):
    '''wrapper around UNICORE job'''
    def __init__(self, transport, job_url):
        super(Job, self).__init__()
        self.transport = transport
        self.job_url = job_url

    @property
    @TimedCache(timeout=REST_CACHE_TIMEOUT)
    def properties(self):
        return self.transport.get(url=self.job_url)

    @property
    def working_dir(self):
        '''return the working directory'''
        return PathDir(
            self.transport,
            self.properties['_links']['workingDirectory']['href'])

    def is_running(self):
        '''checks whether a job is still running'''
        status = self.properties['status']
        return status not in ('SUCCESSFUL', 'FAILED', )

    def abort(self):
        url = self.properties['_links']['action:abort']['href']
        self.transport.post(url=url, json={})

    def restart(self):
        url = self.properties['_links']['action:restart']['href']
        self.transport.post(url=url, json={})

    def start(self):
        url = self.properties['_links']['action:start']['href']
        self.transport.post(url=url, json={})

    @property
    def job_id(self):
        '''get the UID of the job'''
        return os.path.basename(self.job_url)

    def poll(self):
        '''wait until job completes'''
        while self.properties['status'] in ('QUEUED', 'RUNNING'):
            L.debug('Sleeping %s', REST_CACHE_TIMEOUT + 0.1)
            time.sleep(REST_CACHE_TIMEOUT + 0.1)

    def __repr__(self):
        return 'Job: %s: running: %s' % (self.job_id, self.is_running())

    __str__ = __repr__


class Path(object):
    def __init__(self, transport, path_url):
        super(Path, self).__init__()
        self.transport = transport
        self.path_url = path_url

    @property
    @TimedCache(timeout=REST_CACHE_TIMEOUT)
    def properties(self):
        return self.transport.get(url=self.path_url)

    @property
    def path_urls(self):
        urls = self.transport.get(url=self.path_url)['_links']
        return {k: v['href'] for k, v in urls.items()}

    def isdir(self):
        '''is a directory'''
        return False

    def isfile(self):
        '''is a file'''
        return False

    #def get_metadata(self, name):
    #    pass
    
    #def remove(self):
        #'''remove file'''
        #self.transport.delete(url=self.path_urls['files']+"/"+name)
    
    #def rename(self, name):
    #    '''rename file'''
    #    pass


class PathDir(Path):
    def __init__(self, transport, path_url):
        super(PathDir, self).__init__(transport, path_url)

        self._last_contents_lookup = datetime.min
        self._cached_contents = {}

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
                url=os.path.join(self.path_url, 'files', destination),
                headers=headers,
                data=fd)

    def download(self, remote_file, destination=None):
        ''' download remote_file to the current directory, optionally to the given local file '''
        
        assert self.isdir(), 'Not a directory'
        headers = {'Accept': 'application/octet-stream',}
        url = os.path.join(self.path_url, 'files', remote_file)
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
                ret[path] = PathDir(self.transport, path_url)
            else:
                ret[path] = PathFile(self.transport, path_url)
        return ret

    def isdir(self):
        return True

    def mkdir(self, name):
        self.transport.post(url=self.path_urls['files']+"/"+name, json={})

    def rmdir(self, name):
        self.transport.delete(url=self.path_urls['files']+"/"+name)

    def makedirs(self, name):
        self.mkdir(name)


class PathFile(Path):
    def __init__(self, transport, path_url):
        super(PathFile, self).__init__(transport, path_url)

    def read(self, max_size=10**6):
        ''' read complete file into StringIO object, of maximum size `max_size`'''
        file_ = cStringIO.StringIO()
        with closing(
            self.transport.get(url=self.path_url,
                               to_json=False,
                               headers={'Accept': 'application/octet-stream'},
                               stream=True,
                               )) as resp:
            resp.raise_for_status()
            if max_size < int(resp.headers['content-length']):
                raise Exception('File too long')
            file_.write(resp.content)
        return file_

    def download(self, destination):
        ''' download file to the given local file '''
        headers = {'Accept': 'application/octet-stream',}
        resp = self.transport.get(to_json=False, url=self.path_url, headers=headers, stream=True)
        resp.raise_for_status()
        with open(destination, 'wb') as fd:
            for chunk in resp.iter_content(chunk_size=512):
                fd.write(chunk)

    def raw(self):
        ''' access the raw http response for streaming purposes '''
        headers = {'Accept': 'application/octet-stream',}
        resp = self.transport.get(to_json=False, url=self.path_url, headers=headers, stream=True)
        resp.raise_for_status()
        return resp.raw

    def isfile(self):
        return True
