'''Client for Unicore'''
#TODO:
# - Add site picking
# - Add Application discovery and launch creation

import cStringIO
import logging
import os
import re
import time

from contextlib import closing
from datetime import datetime, timedelta

import requests

L = logging.getLogger(__name__)
requests.packages.urllib3.disable_warnings()
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


def get_sites(transport, registry_url=_HBP_REGISTRY_URL):
    resp = transport.get(url=registry_url)
    site_urls = (prop['href']
                 for prop in resp['entries']
                 if prop['type'] == 'TargetSystemFactory')
    sites = dict(reversed(_FACTORY_RE.match(site).groups())
                 for site in site_urls)
    return sites


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
    def __init__(self, oidc_token):
        super(Transport, self).__init__()
        self.oidc_token = oidc_token

    def _headers(self, kwargs):
        headers = {'Authorization': 'Bearer %s' % self.oidc_token,
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


class Client(object):
    '''Entrypoint to Unicore API

        >>> base_url = '...'
        >>> token = '...'
        >>> transport = Transport(token)
        >>> client = Client(transport, base_url)
        >>> # to get the jobs
        >>> client.get_jobs()
        >>> # to start a new job:
        >>> client.new_job(...)

    '''
    def __init__(self, transport, site_url):
        super(Client, self).__init__()
        self.transport = transport
        self.site_url = site_url
        self.site_urls = {
            k: v['href']
            for k, v in self.transport.get(url=site_url)['_links'].items()}

    def get_jobs(self):
        return [Job(self.transport, url)
                for url in self.transport.get(url=self.site_urls['jobs'])['jobs']]

    def new_job(self, cmd):
        launch_params = {'Executable': cmd,
                         }
        resp = self.transport.post(url=self.site_urls['jobs'],
                                   json=launch_params)
        job_url = resp.headers['Location']
        return Job(self.transport, job_url)


class Application(object):
    '''wrapper around Unicore job'''
    def __init__(self, transport, app_url):
        super(Job, self).__init__()
        self.transport = transport
        self.app_url = app_url


class Job(object):
    '''wrapper around unicore job'''
    def __init__(self, transport, job_url):
        super(Job, self).__init__()
        self.transport = transport
        self.job_url = job_url

    @property
    @TimedCache(timeout=_REST_CACHE_TIMEOUT)
    def properties(self):
        return self.transport.get(url=self.job_url)

    @property
    @TimedCache(timeout=3600)
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
            L.debug('Sleeping %s', _REST_CACHE_TIMEOUT + 0.1)
            time.sleep(_REST_CACHE_TIMEOUT + 0.1)

    def __repr__(self):
        return 'Job: %s: running: %s' % (self.job_id, self.is_running())

    __str__ = __repr__


class Path(object):
    def __init__(self, transport, path_url):
        super(Path, self).__init__()
        self.transport = transport
        self.path_url = path_url

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
    #def remove(self, name):
    #    '''remove file'''
    #    pass
    #def rename(self, name):
    #    '''rename file'''
    #    pass


class PathDir(Path):
    def __init__(self, transport, path_url):
        super(PathDir, self).__init__(transport, path_url)

        self._last_contents_lookup = datetime.min
        self._cached_contents = {}

    @property
    @TimedCache(timeout=_REST_CACHE_TIMEOUT)
    def contents(self):
        return self.transport.get(url=self.path_urls['files'])

    def upload(self, input_name):
        '''upload path `input_name` to the directory'''
        assert self.isdir(), 'Not a directory'
        path = os.path.basename(input_name)
        headers = {'Content-Type': 'application/octet-stream',
                   }
        with open(input_name, 'rb') as fd:
            resp = self.transport.put(
                url=os.path.join(self.path_url, 'files', path),
                headers=headers,
                data=fd)

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

    #def mkdir(self, name):
    #    pass
    #def rmdir(self, name):
    #    pass
    #def makedirs(self, name):
    #    pass


class PathFile(Path):
    def __init__(self, transport, path_url):
        super(PathFile, self).__init__(transport, path_url)

    def download(self, max_size=10**6):
        '''download file into StringIO object, of maximum size `max_size`'''
        file_ = cStringIO.StringIO()
        with closing(
            self.transport.get(url=self.path_url,
                               headers={'Accept': 'application/octet-stream'},
                               stream=True,
                               to_json=False,
                               )) as resp:
            resp.raise_for_status()
            if max_size < int(resp.headers['content-length']):
                raise Exception('File too long')
            file_.write(resp.content)
        return file_

    def isfile(self):
        return True
