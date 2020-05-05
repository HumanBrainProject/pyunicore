import requests
import json
import time
from re import match
from contextlib import closing

requests.packages.urllib3.disable_warnings()

"""
Helper methods for using the UNICORE REST API

For a full API reference and examples, have a look at
https://sourceforge.net/p/unicore/wiki/REST_API
https://sourceforge.net/p/unicore/wiki/REST_API_Examples
"""

_HBP_REGISTRY_URL = "https://hbp-unic.fz-juelich.de:7112/HBP/rest/registries/default_registry"

def get_sites(registry_url=None, headers={}):
    """ read the base URLs of the available sites from the registry.
        If the registry_url is None, the HBP registry is used.
    """
    if registry_url is None:
        registry_url = _HBP_REGISTRY_URL
    my_headers = headers.copy()
    my_headers['Accept']="application/json"
    r = requests.get(registry_url, headers=my_headers, verify=False)
    if r.status_code!=200:
        raise RuntimeError("Error accessing registry at %s: %s" % (registry_url, r.status_code))
    sites = {}
    for x in r.json()['entries']:
        try:
            # just want the "core" URL and the site ID
            href = x['href']
            service_type = x['type']
            if "TargetSystemFactory" == service_type:
                base = match(r"(https://\S+/rest/core).*", href).group(1)
                site_name = match(r"https://\S+/(\S+)/rest/core", href).group(1)
                sites[site_name]=base
        except:
            pass
    return sites


def site_info(sites, headers={}):
    """ get access information for all the sites """
    site_info={}
    for site_id in sites.keys():
        info = {}
        try:
            props = get_properties(sites[site_id], headers)
            info['status'] = "OK"
            info['access_type'] = props['client']['role']['selected']
            if info['access_type'] == "user":
                info['groups'] = props['client']['xlogin']['availableGroups']
        except:
            info['status'] = "Error accessing"
        site_info[site_id] = info
    return site_info
    
def get_properties(resource, headers={}):
    """ get JSON properties of a resource """
    my_headers = headers.copy()
    my_headers['Accept']="application/json"
    with closing(requests.get(resource, headers=my_headers, verify=False)) as r:
        if r.status_code!=200:
            raise RuntimeError("Error getting properties: %s" % r.status_code)
        else:
            return r.json()


def get_working_directory(job, headers={}, properties=None):
    """ returns the URL of the working directory resource of a job """
    if properties is None:
        properties = get_properties(job,headers)
    return properties['_links']['workingDirectory']['href']


def invoke_action(resource, action, headers, data={}):
    my_headers = headers.copy()
    my_headers['Content-Type']="application/json"
    action_url = get_properties(resource, headers)['_links']['action:'+action]['href']
    with closing(requests.post(action_url,data=json.dumps(data), headers=my_headers, verify=False)) as r:
        if r.status_code!=200:
            raise RuntimeError("Error invoking action: %s" % r.status_code)
        return r.json()


def upload(destination, file_desc, headers):
    """ upload a file. The file_desc is a dictionary containing the target file name and 
        the data to be uploaded.
    """
    my_headers = headers.copy()
    my_headers['Content-Type']="application/octet-stream"
    name = file_desc['To']
    data = file_desc['Data']
    # TODO file_desc could refer to local file
    with closing(requests.put(destination+"/"+name, data=data, headers=my_headers, verify=False)) as r:
        if r.status_code!=204:
            raise RuntimeError("Error uploading data: %s" % r.status_code)

def download(source, destination, headers):
    """ download a file. The source is the full URL to the file, the destination
        a local filename
    """
    my_headers = headers.copy()
    my_headers['Accept']="application/octet-stream"
    with requests.get(source, headers=my_headers, stream=True, verify=False) as r:
        if r.status_code!=200:
            raise RuntimeError("Error downloading data: %s" % r.status_code)
        else:
            with open(destination, 'wb') as fd:
                for chunk in r.iter_content(chunk_size=512):
                    fd.write(chunk)

def submit(url, job, headers, inputs=[]):
    """
    Submits a job to the given URL, which can be the ".../jobs" URL
    or a ".../sites/site_name/" URL
    If inputs is not empty, the listed input data files are
    uploaded to the job's working directory, and a "start" command is sent
    to the job.
    """
    my_headers = headers.copy()
    my_headers['Content-Type']="application/json"
    if len(inputs)>0:
        # make sure UNICORE does not start the job 
        # before we have uploaded data
        job['haveClientStageIn']='true'

    with closing(requests.post(url,data=json.dumps(job), headers=my_headers, verify=False)) as r:
        if r.status_code!=201:
            raise RuntimeError("Error submitting job: %s" % r.status_code)
        else:
            jobURL = r.headers['Location']

    #  upload input data and explicitely start job
    if len(inputs)>0:
        working_directory = get_working_directory(jobURL, headers)
        for input in inputs:
            upload(working_directory+"/files", input, headers)
        invoke_action(jobURL, "start", headers)
    
    return jobURL

    
def is_running(job, headers={}):
    """ checks whether a job is still running """
    properties = get_properties(job,headers)
    status = properties['status']
    return ("SUCCESSFUL"!=status) and ("FAILED"!=status)


def wait_for_completion(job, headers={}, refresh_function=None, refresh_interval=360):
    """ wait until job is done 
        if refresh_function is not none, it will be called to refresh
        the "Authorization" header. The refresh_interval is in seconds
    """
    sleep_interval = 10
    do_refresh = refresh_function is not None
    # refresh every N iterations
    refresh = int(1 + refresh_interval / sleep_interval)
    count = 0;
    while is_running(job, headers):
        time.sleep(sleep_interval)
        count += 1
        if do_refresh and count == refresh:
            headers['Authorization'] = refresh_function()
            count=0


def file_exists(wd, name, headers):
    """ check if a file with the given name exists
        if yes, return its URL
        of no, return None
    """
    files_url = get_properties(wd, headers)['_links']['files']['href']
    children = get_properties(files_url, headers)['children']
    return name in children or "/"+name in children


def get_file_content(file_url, headers, check_size_limit=True, MAX_SIZE=2048000):
    """ download binary file data """
    if check_size_limit:
        size = get_properties(file_url, headers)['size']
        if size>MAX_SIZE:
            raise RuntimeError("File size too large!")
    my_headers = headers.copy()
    my_headers['Accept']="application/octet-stream"
    r = requests.get(file_url, headers=my_headers, verify=False)
    if r.status_code!=200:
        raise RuntimeError("Error getting file data: %s" % r.status_code)
    else:
        return r.content

def list_files(dir_url, auth, path="/"):
    """ list files in the given directory """
    return get_properties(dir_url+"/files"+path, auth)['children']


def delete(resource, headers={}):
    """ Delete (destroy) a resource """
    my_headers = headers.copy()
    my_headers['Accept']="application/json"
    with closing(requests.delete(resource, headers=my_headers, verify=False)) as r:
        if r.status_code>399:
            raise RuntimeError("Error deleting: %s" % r.status_code)

def get_auth_header(token):
    """ returns Authorization HTTP header using the given token.
        For OIDC auth in the collaboratory, use "Bearer "+oauth.get_token()
    """
    if token is None:
        raise Exception("Authorization header value is required")
    return {'Authorization': token}
