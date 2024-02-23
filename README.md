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

This project has received funding from the European Union’s 
Horizon 2020 Framework Programme for Research and Innovation under the 
Specific Grant Agreement Nos. 720270, 785907 and 945539 
(Human Brain Project SGA 1, 2 and 3)

See LICENSE file for licensing information

## Documentation

The complete documentation of PyUNICORE can be viewed 
[here](https://pyunicore.readthedocs.io/en/latest/)
 
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

## Basic usage

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

PyUNICORE supports a variety of 
[authentication options](https://pyunicore.readthedocs.io/en/latest/authentication.html).

### Run a job and read result files

```Python
my_job = {'Executable': 'date'}

job = client.new_job(job_description=my_job, inputs=[])
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

[More...](https://pyunicore.readthedocs.io/en/latest/uftp.html#using-uftp-for-pyfilesystem)

### Mounting remote filesystems via UFTP

PyUNICORE contains a FUSE driver based on [fusepy](https://pypi.org/project/fusepy),
allowing you to mount a remote filesystem via UFTP. Mounting is a two step process,

  * authenticate to an Auth server, giving you the UFTPD host/port and one-time password
  * run the FUSE driver

[More...](https://pyunicore.readthedocs.io/en/latest/uftp.html#mounting-remote-filesystems-via-uftp)

## Tunneling / port forwarding

Opens a local server socket for clients to connect to, where traffic
gets forwarded to a service on a HPC cluster login (or compute) node.
This feature requires UNICORE 9.1.0 or later on the server side.

You can use this feature in two ways

 * in your own applications via the `pyunicore.client.Job` class.
 * you can also open a tunnel from the command line using the
   'pyunicore.forwarder' module

[More...](https://pyunicore.readthedocs.io/en/latest/port_forwarding.html)

## Dask cluster implementation (experimental)

PyUNICORE provides an implementation of a Dask Cluster, allowing to
run the Dask client on your local host (or in a Jupyter notebook in
the Cloud), and have the Dask scheduler and workers running remotely
on the HPC site.

[More...](https://pyunicore.readthedocs.io/en/latest/dask.html)


### Convert a CWL job to UNICORE

PyUNICORE provides a tool to convert a CWL CommanLineTool and input into a
UNICORE job file. Given the following YAML files that describe a
CommandLineTool wrapper for the echo command and an input file:

```yaml
# echo.cwl

cwlVersion: v1.2

class: CommandLineTool
baseCommand: echo

inputs:
  message:
    type: string
    inputBinding:
      position: 1

outputs: []
```

```yaml
# hello_world.yml

message: "Hello World"
```

A UNICORE job file can be generated using the following command:

```bash
unicore-cwl-runner echo.cwl hello_world.yml > hello_world.u
```

## Helpers

The `pyunicore.helpers` module provides a set of higher-level APIs:

* Connecting to
  * a Registry (`pyunicore.helpers.connect_to_registry`).
  * a site via a Registry URL (`pyunicore.helpers.connect_to_site_from_registry`).
  * a site via its core URL (`pyunicore.helpers.connect_to_site`).
* Defining descriptions as a dataclass and easily converting to a `dict` as required by `pyunicore.client.Client.new_job` via a `to_dict()` method:
  * `pyunicore.helpers.jobs.Description` for `pyunicore.client.Client.new_job()`
  * `pyunicore.helpers.workflows.Description` for `pyunicore.client.WorkflowService.new_workflow()`
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
