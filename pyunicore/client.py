'''Client for Unicore

Based on https://sourceforge.net/p/unicore/wiki/REST_API/
'''

# TODO:
# - Add Application discovery and launch creation
#   >>> BSP = client.get_application('BSP')
#   >>> BSP('foo', 'bar', 'baz')  # to launch it

# - Turn off verify=False once certificates are correct

import logging
import os
import re
import time
import sys

from contextlib import closing
from datetime import datetime, timedelta

import requests


if sys.version_info < (3, 0):
    from types import StringType
else:
    StringType = str  # pragma: no cover

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
    def __init__(self, oidc_token, verify=False):
        super(Transport, self).__init__()
        self.oidc_token = oidc_token
        # TODO: should default to True once certificates are correct
        self.verify = verify

    def _headers(self, kwargs):
        '''required headers for REST calls'''
        headers = {'Authorization': 'Bearer %s' % self.oidc_token,
                   'Accept': 'application/json',
                   }

        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
            del kwargs['headers']

        return headers

    def get(self, to_json=True, **kwargs):
        '''do get

        Note:
            For the raw response, set `to_json` to false
        '''
        headers = self._headers(kwargs)
        req = requests.get(headers=headers, verify=self.verify, **kwargs)
        req.raise_for_status()
        if not to_json:
            return req
        return req.json()

    def put(self, **kwargs):
        '''do put'''
        headers = self._headers(kwargs)
        req = requests.put(headers=headers, verify=self.verify, **kwargs)
        req.raise_for_status()
        return req

    def post(self, **kwargs):
        '''do post'''
        headers = self._headers(kwargs)
        req = requests.post(headers=headers, verify=self.verify, **kwargs)
        req.raise_for_status()
        return req


class Client(object):
    '''Entrypoint to Unicore API

        >>> token = '...'
        >>> transport = Transport(token)
        >>> sites = get_sites(transport)
        >>> client = Client(transport, sites['HBP_JULIA'])
        >>> # to get the jobs
        >>> jobs = client.get_jobs()
        >>> # to start a new job:
        >>> launch_params = {'Executable': cmd,
        >>> }
        >>> job = client.new_job(launch_params)
    '''
    def __init__(self, transport, site_url):
        super(Client, self).__init__()
        self.transport = transport
        self.site_url = site_url
        self.site_urls = {
            k: v['href']
            for k, v in self.transport.get(url=site_url)['_links'].items()}

    def get_jobs(self):
        '''return a list of `Job` objects'''
        return [Job(self.transport, url)
                for url in self.transport.get(url=self.site_urls['jobs'])['jobs']]

    def new_job(self, launch_params):
        '''create a new job by launching `cmd`'''
        resp = self.transport.post(url=self.site_urls['jobs'],
                                   json=launch_params)
        job_url = resp.headers['Location']
        return Job(self.transport, job_url)


class Job(object):
    '''wrapper around unicore job'''
    def __init__(self, transport, job_url):
        super(Job, self).__init__()
        self.transport = transport
        self.job_url = job_url

    @TimedCacheProperty(timeout=_REST_CACHE_TIMEOUT)
    def properties(self):
        '''properties of the job'''
        return self.transport.get(url=self.job_url)

    @TimedCacheProperty(timeout=3600)
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
        self.transport.post(url=url, json={})

    def restart(self):
        '''restart the job'''
        url = self.properties['_links']['action:restart']['href']
        self.transport.post(url=url, json={})

    def start(self):
        '''start the job'''
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
        return ('Job: %s: %s, submitted: %s running: %s' %
                (self.job_id,
                 os.path.basename(self.properties['_links']['self']['href']),
                 self.properties['submissionTime'],
                 self.is_running()))

    __str__ = __repr__


class Path(object):
    def __init__(self, transport, path_url, name):
        super(Path, self).__init__()
        self.transport = transport
        self.path_url = path_url
        self.name = name

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

    def __repr__(self):
        return '%s: %s' % (self.__class__.__name__, self.name)

    __str__ = __repr__


class PathDir(Path):
    def __init__(self, transport, path_url, name):
        super(PathDir, self).__init__(transport, path_url, name)

        self._last_contents_lookup = datetime.min
        self._cached_contents = {}

    @TimedCacheProperty(timeout=_REST_CACHE_TIMEOUT)
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

    #def mkdir(self, name):
    #    pass
    #def rmdir(self, name):
    #    pass
    #def makedirs(self, name):
    #    pass
    #def remove(self, name):
    #    '''remove file'''
    #    pass


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
            downloaded

            >>> import cStringIO
            >>> foo = wd.listdir()['foo.txt']
            >>> foo_contents = cStringIO.StringIO()
            >>> foo.download(foo_contents)
            >>> print(foo.contents.getvalue())
        '''

        with closing(
            self.transport.get(url=self.path_url,
                               headers={'Accept': 'application/octet-stream'},
                               stream=True,
                               to_json=False,
                               )) as resp:
            resp.raise_for_status()
            if max_size < int(resp.headers['content-length']):
                raise Exception('File too long')

            if isinstance(file_, StringType):
                CHUNK_SIZE = 10 * 1024
                with open(file_, 'wb') as fd:
                    for chunk in resp.iter_content(CHUNK_SIZE):
                        fd.write(chunk)
            else:
                file_.write(resp.content)

    def isfile(self):
        return True
