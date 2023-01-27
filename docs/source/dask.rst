Dask integration
----------------

PyUNICORE provides the ``UNICORECluster`` class, which is an implementation
of a Dask Cluster, allowing to run the Dask client on your local host (or in
a Jupyter notebook in the Cloud), and have the Dask scheduler and workers
running remotely on the HPC site.

Here is a basic usage example:

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


Configuration
~~~~~~~~~~~~~

When creating the ``UNICORECluster``, a number of parameters can be set via the constructor.
All parameters except for the submitter to be used are OPTIONAL.

- `submitter`:            this is either a Client object or an Allocation, which is used to submit new jobs
- `n_workers`:            initial number of workers to launch
- `queue`:                the batch queue to use
- `project`:              the accounting project
- `threads`:              worker option controlling the number of threads per worker
- `processes`:            worker option controlling the number of worker processes per job (default: 1)
- `scheduler_job_desc`:   base job description for launching the scheduler (default: None)
- `worker_job_desc`:      base job description for launching a worker (default: None)
- `local_port`:           which local port to use for the Dask client (default: 4322)
- `connect_dashboard`:    if True, a second forwarding process will be lauched to allow a connection to the dashboard
  (default: False)
- `local_dashboard_port`: which local port to use for the dashboard (default: 4323)
- `debug`:                if True, print some debug info (default: False)
- `connection_timeout`:   timeout in seconds while setting up the port forwarding (default: 120)


Customizing the scheduler and workers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, the Dask extension will launch the Dask components using server-side applications
called ``dask-scheduler`` and ``dask-worker``, which need to be defined in the UNICORE IDB.

The job description will look like this:

.. code:: json

  {
  	"ApplicationName": "dask-scheduler",
  	"Arguments":  [
  	  "--port", "0",
  	  "--scheduler-file", "./dask.json"
  	],
  	"Resources": {
  		"Queue": "your_queue",
  		"Project": "your_project"
  	}
  }

If you want to customize this, you can pass in a basic job description when creating
the ``UNICORECluster`` object.

The job descriptions need not contain all command-line arguments, the ``UNICORECluster``
will add them as required. Also, the queue and project will be set if necessary.


For example

.. code:: python

  # Custom job to start scheduler

  sched_jd = {
  	"Executable" : "conda run -n dask dask-scheduler",
  	"Resources": {
  		"Runtime": "2h"
  	},
  	"Tags": ["dask", "testing"]
  }

  # Custom job to start worker

  worker_jd = {
  	"Executable" : "srun --tasks=1 conda run -n dask dask-scheduler",
  	"Resources": {
  		"Nodes": "2"
  	}
  }

  # Create the UNICORECluster instance
  uc_cluster = uc_dask.UNICORECluster(
     submitter,
     queue = "batch",
     project = "my-project",
     scheduler_job_desc=sched_jd,
     worker_job_desc=worker_jd
     )


Scaling
~~~~~~~

To control the number of worker processes and threads, the UNICORECluster has the scale() method,
as well as two properties that can be set from the constructor, or later at runtime

The scale() method controls how many workers (or worker jobs when using "jobs=..." as argument)
are running.

.. code:: python

  # Start two workers
  uc_cluster.scale(2, wait_for_startup=True)

  # Or start two worker jobs with 4 workers per job
  # and 128 threads per worker
  uc_cluster.processes =   4
  uc_cluster.threads   = 128
  uc_cluster.scale(jobs=2)

The dashboard
~~~~~~~~~~~~~

By default a connection to the scheduler's dashboard is not possible. To allow connecting to
the dashboard, set ``connect_dashboard=True`` when creating the ``UNICORECluster``.
The dashboard will then be available at ``http://localhost:4323``, the port can be changed,
if necessary.


Using an allocation
~~~~~~~~~~~~~~~~~~~

To speed up the startup and scaling process, it is possible to pre-allocate a multinode batch job
(if the server side UNICORE supports this, i.e. runs UNICORE 9.1 and Slurm), and run the Dask
components in this allocation.

.. code:: python

  import pyunicore.client as uc_client
  import pyunicore.credentials as uc_credentials
  import pyunicore.dask as uc_dask

  # Create a UNICORE client for accessing the HPC cluster
  base_url = "https://localhost:8080/DEMO-SITE/rest/core"
  credential = uc_credentials.UsernamePassword("demouser", "test123")
  submitter = uc_client.Client(credential, base_url)

  # Allocate a 4-node job
  allocation_jd = {
  	"Job type": "ALLOCATE",

  	"Resources": {
  		"Runtime": "60m",
  		"Queue": "batch",
  		"Project": "myproject"
  	}
  }

  allocation = submitter.new_job(allocation_jd)
  allocation.wait_until_available()

  # Create the UNICORECluster instance using the allocation

  uc_cluster = uc_dask.UNICORECluster(allocation, debug=True)


Note that in this case your custom scheduler / worker job descriptions MUST use ``srun --tasks=1 ...``
to make sure that exactly one scheduler / worker is started on one node.

Also make sure to not lauch more jobs than you have nodes - otherwise the new jobs will stay "QUEUED".
