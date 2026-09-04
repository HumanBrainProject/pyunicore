Async API
---------

The async API offers the same features as the sync API,
except every method that uses HTTP calls to the UNICORE server
is asynchronous.

Creating a client for a UNICORE site
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The async API is in the 'pyunicore.aio.client' package.

.. code:: python

  import pyunicore.aio.client as uc_client
  import pyunicore.credentials as uc_credentials
  import json

  base_url = "https://localhost:8080/DEMO-SITE/rest/core"

  # authenticate with username/password
  credential = uc_credentials.UsernamePassword("demouser", "test123")

  client = uc_client.Client(credential, base_url)
  print(json.dumps(await client.properties, indent = 2))


Running a job and read result files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

  my_job = {'Executable': 'date'}

  job = await client.new_job(job_description=my_job, inputs=[])
  print(json.dumps(await job.properties, indent = 2))

  await job.poll() # wait for job to finish

  work_dir = await job.working_dir
  print(json.dumps(await work_dir.properties, indent = 2))

  stdout = awai work_dir.stat("/stdout")
  print(json.dumps(await stdout.properties, indent = 2))
  content = await stdout.read()
  print(content)



Connect to a Registry and list all registered services
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

  registry_url = "https://localhost:8080/REGISTRY/rest/registries/default_registry"

  # authenticate with username/password
  credential = uc_credentials.UsernamePassword("demouser", "test123")

  r = uc_client.Registry(credential, registry_url)
  print(await r.site_urls)


More examples
~~~~~~~~~~~~~

Further examples for using PyUNICORE can be found in the "integration-tests"
folder in the source code repository.
