Dask integration
----------------

PyUNICORE provides an implementation of a Dask Cluster, allowing to
run the Dask client on your local host (or in a Jupyter notebook in
the Cloud), and have the Dask scheduler and workers running remotely
on the HPC site.

A basic usage example:

.. code:: python

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


That's it! Now Dask will run its computations using the scheduler
and workers started via UNICORE on the HPC site.
