'''
    Client for UNICORE using the REST API

    For full info on the REST API, see https://sourceforge.net/p/unicore/wiki/REST_API/
'''

import logging
import os
import re
import json

import requests
import time
import sys
from contextlib import closing
from datetime import datetime, timedelta
from ftplib import FTP
from jwt import decode as jwt_decode, ExpiredSignatureError

if sys.version_info < (3, 0):
    from types import StringType
else:
    StringType = str  # pragma: no cover

# TODO:
# - Add Application discovery and launch creation
#   >>> BSP = client.get_application('BSP')
#   >>> BSP('foo', 'bar', 'baz')  # to launch it

# - Turn off verify=False once certificates are correct

# - Add feature to set preferences (xlogin, role, ...) on transport

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
    '''wrapper around requests, which
           - adds Authorization header (Basic or Bearer style)
           - transparently handles security sessions
           - handles user preferences
           - can be configured with an OIDC refresh handler

       see https://sourceforge.net/p/unicore/wiki/REST_API/#user-preferences
       see https://sourceforge.net/p/unicore/wiki/REST_API/#security-session-handling
    '''
    def __init__(self, auth_token, oidc=True, verify=False, refresh_handler=None, use_security_sessions=True):
        super(Transport, self).__init__()
        self.auth_token = auth_token
        self.oidc = oidc
        # TODO: should default to True once certificates are correct
        self.verify = verify
        self.refresh_handler = refresh_handler
        self.use_security_sessions = use_security_sessions
        self.last_session_id = None
        self.preferences = None

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
        if self.use_security_sessions:
            self.last_session_id = res.headers.get('X-UNICORE-SecuritySession', None)

        if 500 <= res.status_code < 600:
            reason = res.reason
            try:
                json = res.json()
                reason = json['errorMessage']
            except Exception as e:
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

    def _head(self, **kwargs):
        '''do a HEAD request to make sure current security session is OK'''
        if self.use_security_sessions:
            headers = self._headers({})
            res = requests.head(headers=headers, verify=self.verify, url=kwargs['url'])
            if self.repeat_required(res, headers):
                res = requests.head(headers=headers, verify=self.verify, url=kwargs['url'])
            self.last_session_id = res.headers.get('X-UNICORE-SecuritySession', None)
            res.close()

    def get(self, to_json=True, **kwargs):
        '''do get

        Note:
            For the complete response, set `to_json` to false
        '''
        headers = self._headers(kwargs)
        res = requests.get(headers=headers, verify=self.verify, **kwargs)
        if self.repeat_required(res, headers):
            res = requests.get(headers=headers, verify=self.verify, **kwargs)
        self.checkError(res)
        if not to_json:
            return res
        json = res.json()
        res.close()
        return json

    def put(self, **kwargs):
        '''do put'''
        self._head(**kwargs)
        headers = self._headers(kwargs)
        res = requests.put(headers=headers, verify=self.verify, **kwargs)
        self.checkError(res)
        return res

    def post(self, **kwargs):
        '''do post'''
        self._head(**kwargs)
        headers = self._headers(kwargs)
        res = requests.post(headers=headers, verify=self.verify, **kwargs)
        self.checkError(res)
        return res

    def delete(self, **kwargs):
        headers = self._headers(kwargs)
        with closing(requests.delete(headers=headers, verify=self.verify, **kwargs)) as res:
            self.checkError(res)


class Resource(object):
    ''' Base class for a UNICORE resource with properties and some common methods'''

    def __init__(self, transport, resource_url):
        super(Resource, self).__init__()
        self.transport = transport
        self.resource_url = resource_url

    @TimedCacheProperty(timeout=_REST_CACHE_TIMEOUT)
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
        >>> sites = get_sites(transport)
        >>> client = Client(transport, sites['HBP_JULIA'])
        >>> # to get the jobs
        >>> jobs = client.get_jobs()
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

    @TimedCacheProperty(timeout=_REST_CACHE_TIMEOUT)
    def properties(self):
        return self.transport.get(url=self.site_url)

    def access_info(self):
        return self.properties['client']

    def get_storages(self):
        return [Storage(self.transport, url)
                for url in self.transport.get(url=self.site_urls['storages'])['storages']]

    def get_applications(self):
        apps = []
        for url in self.transport.get(url=self.site_urls['factories'])['factories']:
            for app in self.transport.get(url=url)['applications']:
                apps.append(Application(self.transport, url+"/applications/"+app))
        return apps

    def get_jobs(self):
        '''return a list of `Job` objects'''
        return [Job(self.transport, url)
                for url in self.transport.get(url=self.site_urls['jobs'])['jobs']]

    def new_job(self, job_description, inputs=[]):
        ''' submit and start a batch job on the site, optionally uploading input data files '''
        if len(inputs)>0 or job_description.get('haveClientStageIn') is True :
            job_description['haveClientStageIn'] = "true"

        with closing(self.transport.post(url=self.site_urls['jobs'], json=job_description)) as resp:
            job_url = resp.headers['Location']
        
        job = Job(self.transport, job_url)

        if len(inputs)>0:
            working_dir = job.working_dir
            for input in inputs:
                working_dir.upload(input)
        if job_description.get('haveClientStageIn', None) == "true":
            try:
                job.start()
            except:
                pass

        return job


    def execute(self, cmd):
        ''' run a (non-batch) command on the site '''
        job_description = {'Executable': cmd,
                           'Job type': 'INTERACTIVE',
                           'Environment': {'UC_PREFER_INTERACTIVE_EXECUTION':'true'},
        }
        with closing(self.transport.post(url=self.site_urls['jobs'], json=job_description)) as resp:
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


class Job(Resource):
    '''wrapper around UNICORE job'''

    def __init__(self, transport, job_url):
        super(Job, self).__init__(transport, job_url)

    @TimedCacheProperty(timeout=3600)
    def working_dir(self):
        '''return the Storage for accessing the working directory '''
        return Storage(
            self.transport,
            self.properties['_links']['workingDirectory']['href'])

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
            L.debug('Sleeping %s', _REST_CACHE_TIMEOUT + 0.1)
            time.sleep(_REST_CACHE_TIMEOUT + 0.1)

    def __repr__(self):
        return ('Job: %s: %s, submitted: %s running: %s' %
                (self.job_id,
                 os.path.basename(self.properties['_links']['self']['href']),
                 self.properties['submissionTime'],
                 self.is_running()))

    __str__ = __repr__


class Storage(Resource):
    ''' wrapper around a UNICORE Storage resource '''

    def __init__(self, transport, storage_url):
        super(Storage, self).__init__(transport, storage_url)
        self.storage_url = storage_url

    @property
    def path_urls(self):
        urls = self.transport.get(url=self.resource_url)['_links']
        return {k: v['href'] for k, v in urls.items()}

    def contents(self, path="/"):
        return self.transport.get(url=self.path_urls['files']+'/'+path)

    def stat(self, path):
        ''' get a file/directory '''
        path_url = self.path_urls['files'] + '/' + path
        headers = {'Accept': 'application/json',}
        props = self.transport.get(url=path_url, headers = headers)
        if props['isDirectory']:
            ret = PathDir(self, path_url, path)
        else:
            ret = PathFile(self, path_url, path)
        return ret
    
    def listdir(self, base='/'):
        ''' get a list of the files and directories in the given base directory '''
        ret = {}
        for path, meta in self.contents()['content'].items():
            path_url = self.path_urls['files'] + path
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
        return self.transport.post(url=self.path_urls['action:rename'], json=json)

    def copy(self, source, target):
        '''copy a file on this storage'''
        json = {'from': source,
                'to': target,
                }
        return self.transport.post(url=self.path_urls['action:copy'], json=json)

    def mkdir(self, name):
        return self.transport.post(url=self.path_urls['files']+"/"+name, json={})

    def rmdir(self, name):
        return self.transport.delete(url=self.path_urls['files']+"/"+name)

    def rm(self, name):
        return self.transport.delete(url=self.path_urls['files']+"/"+name)

    def makedirs(self, name):
        return self.mkdir(name)

    def upload(self, input_name, destination=None):
        '''upload file "input_name" '''
        if destination is None:
            destination = os.path.basename(input_name)

        headers = {'Content-Type': 'application/octet-stream'}
        with open(input_name, 'rb') as fd:
            resp = self.transport.put(
                url=os.path.join(self.resource_url, "files", destination),
                headers=headers,
                data=fd)

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

    def get_metadata(self, name):
        return self.properties['metadata']['name']
    
    def remove(self):
        '''remove file or directory'''
        return self.storage.rm(name)

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
            file_(StringType or file-like): if a string, a file of that name
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
            if isinstance(file_, StringType):
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


class UFTP(Resource):
    ''' authenticate UFTP transfers and use ftplib to interact with
        the UFTPD server
    '''
    uftp_session_tag = "___UFTP___MULTI___FILE___SESSION___MODE___"

    def __init__(self, transport, base_url):
        super(UFTP, self).__init__(transport, base_url)
        self.refresh()

    def refresh(self):
        self.site_urls = {}
        for entry in self.properties:
            try:
                self.site_urls[entry] = self.properties[entry]['href']
            except Exception as e:
                print("Error: %s" % e)

    def open_session(self, server_name=None, base_dir="", **kwargs):
        ''' open an FTP session at the given UFTP server
        If 'basedir' is not given, the user's home directory is the base dir.
        The ftplib FTP object is returned.
        '''
        if server_name is None:
            url = self.site_urls.values()[0]
        else:
            url = self.site_urls[server_name]
        req = {"serverPath": base_dir+self.uftp_session_tag}
        params = self.transport.post(url=url, json=req).json()
        port = params['serverPort']
        host = params['serverHost']
        pwd  = params['secret']
        ftp = FTP()
        ftp.connect(host,port)
        ftp.login("anonymous", pwd)
        return ftp

    def download(self, remote_file, destination=None, server_name=None, base_dir="", **kwargs):
        ''' download the given remote file, optionally renaming it '''
        ftp = self.open_session(server_name, base_dir)
        if destination is None:
            destination = os.path.basename(remote_file)
        ftp.retrbinary("RETR %s" % remote_file, open(destination, 'wb').write)
        ftp.close()


class Share(Resource):
    ''' UFTP Data Sharing helper '''

    ANONYMOUS = "CN=ANONYMOUS,O=UNKNOWN,OU=UNKNOWN"

    def __init__(self, transport, base_url):
        super(Share, self).__init__(transport, base_url)

    def share(self, path, user, access="READ"):
        ''' create or update a share '''
        req = {"path": path}
        req['access'] = access
        req['user'] = user
        res = self.transport.post(url=self.resource_url, json=req)
        return res.headers['Location']

