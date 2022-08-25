# Python library for using the UNICORE REST API

This library covers the UNICORE REST API, making common tasks like
file access, job submission and management, workflow submission and
management more convenient, and integrating UNICORE features better
with typical Python usage.

For the full, up-to-date documentation of the REST API,
see https://unicore-docs.readthedocs.io/en/latest/user-docs/rest-api

Development of this library was funded in part by the Human Brain Project

For more information about the Human Brain Project, see https://www.humanbrainproject.eu/

See LICENSE file for licensing information

# Getting started with pyUNICORE

Install from PyPI with

    pip install -U pyunicore


Additional packages may be required for your use case:

* Using the UFTP fuse driver requires "fusepy"
* Creating JWT tokens signed with keys requires the "cryptography" package

# Example

## Sample code to create a client for a UNICORE site

    import pyunicore.client as uc_client
    import pyunicore.credentials as uc_credentials
    import json
   
    base_url = "https://localhost:8080/DEMO-SITE/rest/core"

    # authenticate with username/password
    credential = uc_credentials.UsernamePassword("demouser", "test123")
    transport  = uc_client.Transport(credential)
    
    client = uc_client.Client(transport, base_url)
    print(json.dumps(client.properties, indent = 2))
    
## Running a sample job and reading result data
   
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
    
## Connecting to a Registry and listing all registered services

    registry_url = "https://localhost:8080/REGISTRY/rest/registries/default_registry"

    # authenticate with username/password
    credential = uc_credentials.UsernamePassword("demouser", "test123")
    transport = uc_client.Transport(credential)
    
    r = uc_client.Registry(tr, registry_url)
    print(r.site_urls)

 ## Further reading
 
More example code can be found in the "integration-tests" folder in the source code repository.
