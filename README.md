#
# Python library for using the UNICORE REST API
#

See LICENSE file for licensing information

For full documentation of the REST API, see https://sourceforge.net/p/unicore/wiki/REST_API

For more information about the Human Brain Project, see https://www.humanbrainproject.eu/

# Getting started with pyUNICORE

Install from PyPI with

    pip install -U pyunicore
  
Sample code to create a client for a UNICORE site

    import pyunicore.client as unicore_client
    import json, b64encode
   
    base_url = "https://localhost:8080/DEMO-SITE/rest/core"

    # authenticate with username/password
    token = b64encode(b"demouser:test123").decode("ascii")
    transport = unicore_client.Transport(token, oidc=False)
    
    client = unicore_client.Client(transport, base_url)
    print(json.dumps(client.properties, indent = 2))
    
# Running a sample job and reading result data

    my_job = {'Executable': 'date'}
    
    job = site.new_job(job_description=my_job, inputs=[])
    print(json.dumps(job.properties, indent = 2))
    
    job.poll() # wait for job to finish
 
    work_dir = job.working_dir
    print(json.dumps(work_dir.properties, indent = 2))
    
    stdout = work_dir.stat("/stdout")
    print(json.dumps(stdout.properties, indent = 2))
  
    content = stdout.raw().read()
    print(content)
    
