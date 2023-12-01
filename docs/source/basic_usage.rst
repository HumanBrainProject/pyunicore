Getting started
---------------

Creating a client for a UNICORE site
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

  import pyunicore.client as uc_client
  import pyunicore.credentials as uc_credentials
  import json

  base_url = "https://localhost:8080/DEMO-SITE/rest/core"

  # authenticate with username/password
  credential = uc_credentials.UsernamePassword("demouser", "test123")

  client = uc_client.Client(credential, base_url)
  print(json.dumps(client.properties, indent = 2))


Running a job and read result files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

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



Connect to a Registry and list all registered services
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

  registry_url = "https://localhost:8080/REGISTRY/rest/registries/default_registry"

  # authenticate with username/password
  credential = uc_credentials.UsernamePassword("demouser", "test123")

  r = uc_client.Registry(credential, registry_url)
  print(r.site_urls)


More examples
~~~~~~~~~~~~~

Further examples for using PyUNICORE can be found in the "integration-tests"
folder in the source code repository.
