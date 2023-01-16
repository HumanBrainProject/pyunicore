# PyUNICORE, a Python library for using UNICORE and UFTP

This library covers the UNICORE REST API, making common tasks like
file access, job submission and management, workflow submission and
management more convenient, and integrating UNICORE features better
with typical Python usage.

The full, up-to-date documentation of the REST API can be found
[here](https://unicore-docs.readthedocs.io/en/latest/user-docs/rest-api)

In addition, this library contains code for using UFTP (UNICORE FTP)
for filesystem mounts with FUSE, a UFTP driver for
[PyFilesystem](https://github.com/PyFilesystem/pyfilesystem2)
and a UNICORE implementation of a
[Dask Cluster](https://distributed.dask.org/en/stable/)

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

```Python
import pyunicore.client as uc_client
import pyunicore.credentials as uc_credentials
import json

base_url = "https://localhost:8080/DEMO-SITE/rest/core"

# authenticate with username/password
credential = uc_credentials.UsernamePassword("demouser", "test123")

client = uc_client.Client(credential, base_url)
print(json.dumps(client.properties, indent = 2))
```

### Run a job and read result files

```Python
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
```

### Connect to a Registry and list all registered services

```Python
registry_url = "https://localhost:8080/REGISTRY/rest/registries/default_registry"

# authenticate with username/password
credential = uc_credentials.UsernamePassword("demouser", "test123")

r = uc_client.Registry(credential, registry_url)
print(r.site_urls)
```

### Further reading

More examples for using PyUNICORE can be found in the "integration-tests"
folder in the source code repository.

## UFTP examples

### Using UFTP for PyFilesystem

You can create a [PyFilesystem](https://github.com/PyFilesystem/pyfilesystem2) `FS`
object either directly in code, or implicitely via a URL.

The convenient way is via URL:

```Python
from fs import open_fs
fs_url = "uftp://demouser:test123@localhost:9000/rest/auth/TEST:/data"
uftp_fs = open_fs(fs_url)
```

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

```Python
import pyunicore.client as uc_client
import pyunicore.credentials as uc_credentials
import pyunicore.uftp as uc_uftp
import pyunicore.uftpfuse as uc_fuse

_auth = "https://localhost:9000/rest/auth/TEST"
_base_dir = "/opt/shared-data"
_local_mount_dir = "/tmp/mount"

# authenticate
cred = uc_credentials.UsernamePassword("demouser", "test123")
uftp = uc_uftp.UFTP(uc_client.Transport(cred), _auth, _base_dir)
_host, _port, _password  = uftp.authenticate()

# run the fuse driver
fuse = uc_fuse.FUSE(
uc_fuse.UFTPDriver(_host, _port, _password), _local_mount_dir, foreground=False, nothreads=True)
```

### Tunneling / port forwarding

Opens a local server socket for clients to connect to, where traffic
gets forwarded to a service on a HPC cluster login (or compute) node.
This feature requires UNICORE 9.1.0 or later on the server side.

You can use this feature in two ways

 * in your own applications via the `pyunicore.client.Job` class.
 * you can also open a tunnel from the command line using the
   'pyunicore.forwarder' module

Here is an example for a command line tool invocation:

```
LOCAL_PORT=4322
JOB_URL=https://localhost:8080/DEMO-SITE/rest/core/jobs/some_job_id
REMOTE_PORT=8000
python3 -m pyunicore.forwarder  --token <your_auth_token> \
  -L $LOCAL_PORT \
   $JOB_URL/forward-port?port=REMOTE_PORT \
```

Your application can now connect to "localhost:4322" but all traffic
will be forwarded to port 8000 on the login node.

See
```
python3 -m pyunicore.forwarder --help
```
for all options.

### Dask cluster implementation (experimental)

PyUNICORE provides an implementation of a Dask Cluster, allowing to
run the Dask client on your local host (or in a Jupyter notebook in
the Cloud), and have the Dask scheduler and workers running remotely
on the HPC site.

A basic usage example:

```Python
import pyunicore.client as uc_client
import pyunicore.credentials as uc_credentials
import pyunicore.dask as uc_dask

# Create a UNICORE client for accessing the HPC cluster
base_url = "https://localhost:8080/DEMO-SITE/rest/core"
credential = uc_credentials.UsernamePassword("demouser", "test123")
submitter = uc_client.Client(credential, base_url)

# Create the UNICORECluster instance

uc_cluster = uc_dask.UNICORECluster(
   submitter,
   queue = "batch",
   project = "my-project",
   debug=True)

# Start two workers
uc_cluster.scale(2, wait_for_startup=True)

# Create a Dask client connected to the UNICORECluster

from dask.distributed import Client
dask_client = Client(uc_cluster, timeout=120)
```

That's it! Now Dask will run its computations using the scheduler
and workers started via UNICORE on the HPC site.

## Helpers

The `pyunicore.helpers` module provides a set of higher-level APIs:

* Connecting to
  * a Registry (`pyunicore.helpers.connect_to_registry`).
  * a site via a Registry URL (`pyunicore.helpers.connect_to_site_from_registry`).
  * a site via its core URL (`pyunicore.helpers.connect_to_site`).
* Defining descriptions as a dataclass and easily converting to a `dict` as required by `pyunicore.client.Client.new_job` via a `to_dict()` method:
  * `pyunicore.helpers.jobs.Description` for `pyunicore.client.Client.new_job()`
  * `pyunicore.helpers.workflows.Description` for `pyunicore.client.WorkflowService.new_workflow()`
* All possible job statuses that may be returned by the jobs API (`pyunicore.helpers.JobStatus`).
* Defining a workflow description

### Connecting to a Registry

```Python
import json
import pyunicore.credentials as uc_credentials
import pyunicore.helpers as helpers

registry_url = "https://localhost:8080/REGISTRY/rest/registries/default_registry"

credentials = uc_credentials.UsernamePassword("demouser", "test123")

client = helpers.connection.connect_to_registry(
    registry_url=registry_url,
    credentials=credentials,
)
print(json.dumps(client.properties, indent=2))
```

### Connecting to a site via a Registry

```Python
import json
import pyunicore.credentials as uc_credentials
import pyunicore.helpers as helpers

registry_url = "https://localhost:8080/REGISTRY/rest/registries/default_registry"
site = "DEMO-SITE"

credentials = uc_credentials.UsernamePassword("demouser", "test123")

client = helpers.connection.connect_to_site_from_registry(
    registry_url=registry_url,
    site_name=site,
    credentials=credentials,
)
print(json.dumps(client.properties, indent=2))
```

### Connecting to a site directly

```Python
import json
import pyunicore.credentials as uc_credentials
import pyunicore.helpers as helpers

site_url = "https://localhost:8080/DEMO-SITE/rest/core"

credentials = uc_credentials.UsernamePassword("demouser", "test123")

client = helpers.connection.connect_to_site(
    site_api_url=site_url ,
    credentials=credentials,
)
print(json.dumps(client.properties, indent=2))
```

### Defining a job or workflow

```Python
from pyunicore import helpers

client = ...

resources = helpers.jobs.Resources(nodes=4)
job = helpers.jobs.Description(
    executable="ls",
    project="demoproject",
    resources=resources
)

client.new_job(job.to_dict())
```

This works analogously for `pyunicore.helpers.workflows`.

## Contributing

1. Fork the repository
2. Install the development dependencies

   ```bash
   pip install -r requirements-dev.txt
   ```

3. Install pre-commit hooks

   ```bash
   pre-commit install
   ```
