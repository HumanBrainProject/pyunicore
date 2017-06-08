'''Client for Unicore'''
import cStringIO
import logging
import os
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


class UnicoreTransport(object):
    '''wrapper around requests to add authentication headers'''
    def __init__(self, oidc_token):
        super(UnicoreTransport, self).__init__()
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


class UnicoreClient(object):
    '''Entrypoint to Unicore API

        >>> base_url = '...'
        >>> token = '...'
        >>> transport = UnicoreTransport(token)
        >>> client = UnicoreClient(transport, base_url)
        >>> # to get the jobs
        >>> client.get_jobs()
        >>> # to start a new job:
        >>> client.new_job(...)

    '''
    def __init__(self, transport, site_url):
        super(UnicoreClient, self).__init__()
        self.transport = transport
        self.site_url = site_url
        self.site_urls = {
            k: v['href']
            for k, v in self.transport.get(url=site_url)['_links'].items()}

    def get_jobs(self):
        return [UnicoreJob(self.transport, url)
                for url in self.transport.get(url=self.site_urls['jobs'])['jobs']]

    def new_job(self, cmd):
        launch_params = {'Executable': cmd,
                         }
        resp = self.transport.post(url=self.site_urls['jobs'],
                                   json=launch_params)
        job_url = resp.headers['Location']
        return UnicoreJob(self.transport, job_url)


class UnicoreJob(object):
    '''wrapper around unicore job'''
    def __init__(self, transport, job_url):
        super(UnicoreJob, self).__init__()
        self.transport = transport
        self.job_url = job_url

    @property
    @TimedCache(timeout=REST_CACHE_TIMEOUT)
    def properties(self):
        return self.transport.get(url=self.job_url)

    @property
    def working_dir(self):
        '''return the working directory'''
        return UnicorePathDir(
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
        return 'UnicoreJob: %s: running: %s' % (self.job_id, self.is_running())

    __str__ = __repr__


class UnicorePath(object):
    def __init__(self, transport, path_url):
        super(UnicorePath, self).__init__()
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


class UnicorePathDir(UnicorePath):
    def __init__(self, transport, path_url):
        super(UnicorePathDir, self).__init__(transport, path_url)

        self._last_contents_lookup = datetime.min
        self._cached_contents = {}

    @property
    @TimedCache(timeout=REST_CACHE_TIMEOUT)
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
                ret[path] = UnicorePathDir(self.transport, path_url)
            else:
                ret[path] = UnicorePathFile(self.transport, path_url)
        return ret

    def isdir(self):
        return True

    #def mkdir(self, name):
    #    pass
    #def rmdir(self, name):
    #    pass
    #def makedirs(self, name):
    #    pass


class UnicorePathFile(UnicorePath):
    def __init__(self, transport, path_url):
        super(UnicorePathFile, self).__init__(transport, path_url)

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
