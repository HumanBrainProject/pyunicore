# PyUNICORE, a Python library for using UNICORE and UFTP

This library covers the UNICORE REST API, making common tasks like
file access, job submission and management, workflow submission and
management more convenient, and integrating UNICORE features better
with typical Python usage.

The full, up-to-date documentation of the REST API can be found
[here](https://unicore-docs.readthedocs.io/en/latest/user-docs/rest-api)

In addition, this library contains code for using UFTP (UNICORE FTP)
for filesystem mounts with FUSE, and a UFTP driver for
[PyFilesystem](https://github.com/PyFilesystem/pyfilesystem2)

Development of this library was funded in part by the 
[Human Brain Project](https://www.humanbrainproject.eu)

See LICENSE file for licensing information

## Installation

Install from PyPI with

    pip install -U pyunicore

Additional extra packages may be required for your use case:

 * Using the UFTP fuse driver requires "fusepy"
 * Using UFTP with pyfilesystem requires "fs"
 * Creating JWT tokens signed with keys requires the
  "cryptography" package

You can install (one or more) extras with pip:

    pip install -U pyunicore[crypto,fs,fuse]

## Examples

### Creating a client for a UNICORE site

    import pyunicore.client as uc_client
    import pyunicore.credentials as uc_credentials
    import json
   
    base_url = "https://localhost:8080/DEMO-SITE/rest/core"

    # authenticate with username/password
    credential = uc_credentials.UsernamePassword("demouser", "test123")
    transport  = uc_client.Transport(credential)
    
    client = uc_client.Client(transport, base_url)
    print(json.dumps(client.properties, indent = 2))
    
### Run a job and read result files
   
    my_job = {'Executable': 'date'}
    
    job = uc_client.new_job(job_description=my_job, inputs=[])
    print(json.dumps(job.properties, indent = 2))
    
    job.poll() # wait for job to finish
 
    work_dir = job.working_dir
    print(json.dumps(work_dir.properties, indent = 2))
    
    stdout = work_dir.stat("/stdout")
    print(json.dumps(stdout.properties, indent = 2))
  
    content = stdout.raw().read()
    print(content)
    
### Connect to a Registry and list all registered services

    registry_url = "https://localhost:8080/REGISTRY/rest/registries/default_registry"

    # authenticate with username/password
    credential = uc_credentials.UsernamePassword("demouser", "test123")
    transport = uc_client.Transport(credential)
    
    r = uc_client.Registry(tr, registry_url)
    print(r.site_urls)

### Further reading

More examples for using PyUNICORE can be found in the "integration-tests" 
folder in the source code repository.

## UFTP examples

### Using UFTP for PyFilesystem 

You can create a [PyFilesystem](https://github.com/PyFilesystem/pyfilesystem2) `FS`
object either directly in code, or implicitely via a URL.

The convenient way is via URL:

    from fs import open_fs
    fs_url = "uftp://demouser:test123@localhost:9000/rest/auth/TEST:/data"
    uftp_fs = open_fs(fs_url)

The URL format is

    uftp://[username]:[password]@[auth-server-url]:[base-directory]?[token=...][identity=...]
   
The FS driver supports three types of authentication

  * Username/Password - give `username` and `password`
  * SSH Key - give `username` and the `identity` parameter, 
    where `identity` is the filename of a private key.
    Specify the `password` if needed to load the private key
  * Bearer token - give the token value via the `token` parameter

(note: the SSH key authentication using this library requires 
UFTP Auth server 2.7.0 or later)
  
### Mounting remote filesystems via UFTP
  
PyUNICORE contains a FUSE driver based on [fusepy](https://pypi.org/project/fusepy),
allowing you to mount a remote filesystem via UFTP. Mounting is a two step process,

  * authenticate to an Auth server, giving you the UFTPD host/port and one-time password
  * run the FUSE driver

The following code example gives you the basic idea:

    import pyunicore.client as uc_client
    import pyunicore.credentials as uc_credentials
    import pyunicore.uftp as uc_uftp
    import pyunicore.uftpfuse as uc_fuse

    _auth = "https://localhost:9000/rest/auth/TEST"
    _base_dir = "/opt/shared-data"
    _local_mount_dir = "/tmp/mount"

    # auhenticate
    cred = uc_credentials.UsernamePassword("demouser", "test123")
    uftp = uc_uftp.UFTP(uc_client.Transport(cred), _auth, _base_dir)
    _host, _port, _password  = uftp.authenticate()

    # run the fuse driver
    fuse = uc_fuse.FUSE(
        uc_fuse.UFTPDriver(_host, _port, _password), _local_mount_dir,
        foreground=False, nothreads=True)
