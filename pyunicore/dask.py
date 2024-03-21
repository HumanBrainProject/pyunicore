import json
import math
import time
from multiprocessing import get_context
from urllib.parse import urlparse

from distributed.core import rpc
from distributed.core import Status
from distributed.deploy.cluster import Cluster

from pyunicore.client import JobStatus
from pyunicore.forwarder import Forwarder


class UNICORECluster(Cluster):
    """Deploy Dask on a HPC site via UNICORE

    This class will launch a job for the Dask scheduler, and one or more jobs for
    running Dask workers. It supports scale() method to adapt the number of workers.

    Args:

    submitter: this is either a Client object or an Allocation, which is used
               to submit new jobs
    n_workers:            initial number of workers to launch
    queue:                the batch queue to use
    project:              the accounting project
    threads:              worker option controlling the number of threads per worker
    processes:            worker option controlling the number of worker processes per job
    scheduler_job_desc:   base job description for launching the scheduler
    worker_job_desc:      base job description for launching a worker
    local_port:           which local port to use for the Dask client (must be a free port)
    connect_dashboard:    if True, a second forwarding process will be launched
                          to allow a connection to the dashboard
    local_dashboard_port: which local port to use for the dashboard (must be a free port)
    debug:                if True, print some debug info
    connection_timeout:   timeout in seconds while setting up the port forwarding
    """

    def __init__(
        self,
        submitter,
        n_workers=0,
        name=None,
        asynchronous=False,
        queue=None,
        project=None,
        threads=None,
        processes=1,
        scheduler_job_desc={},
        worker_job_desc={},
        local_port=4322,
        connect_dashboard=False,
        local_dashboard_port=4323,
        debug=False,
        connection_timeout=120,
    ):
        super().__init__(asynchronous=asynchronous, name=name, quiet=not debug)
        self.submitter = submitter
        self.status = Status.created
        self.debug = debug
        self.local_port = local_port
        self.connect_dashboard = connect_dashboard
        self.local_dashboard_port = local_dashboard_port
        self.queue = queue
        self.project = project
        self.scheduler_job_desc = scheduler_job_desc
        self.worker_job_desc = worker_job_desc
        self.threads = threads
        self.processes = processes
        self.worker_jobs = []
        self.forwarding_process = None
        self.db_forwarding_process = None
        try:
            self._start_scheduler()
            self._start_forwarder()
            self.scheduler_comm = rpc(
                "tcp://localhost:%s" % self.local_port, timeout=connection_timeout
            )
            print("Scheduler address: ", self.scheduler_comm.address)
            if n_workers:
                self.scale(n_workers)
        except OSError:
            try:
                self.cleanup()
            finally:
                raise
        self._loop_runner.start()
        self.sync(self._start)

    def get_scheduler_job_description(self):
        """creates the JSON job description for starting the scheduler
        Returns JSON and optional array of input files
        """
        job = self.scheduler_job_desc
        if job.get("ApplicationName") is None and job.get("Executable") is None:
            job["ApplicationName"] = "dask-scheduler"
        args = job.get("Arguments", [])
        if "--port" not in args:
            args.append("--port")
            args.append("0")
        if "--scheduler-file" not in args:
            args.append("--scheduler-file")
            args.append("./dask.json")
        job["Arguments"] = args
        resources = job.get("Resources", {})
        if self.queue is not None:
            resources["Queue"] = self.queue
        if self.project is not None:
            resources["Project"] = self.project
        if len(resources) > 0:
            job["Resources"] = resources
        return job, []

    def _start_scheduler(self):
        """
        Starts the scheduler
        """
        job_desc, inputs = self.get_scheduler_job_description()
        job = self.submitter.new_job(job_desc, inputs)
        not self.debug or print("Submitted scheduler", job)
        not self.debug or print("Waiting for scheduler to start up...")
        job.poll(JobStatus.RUNNING)
        if JobStatus.FAILED == job.status:
            raise OSError("Launching scheduler failed")
        not self.debug or print("Scheduler is running.")
        self.scheduler_job = job
        self.scheduler_host, self.scheduler_port = self._read_scheduler_address()

    def _read_scheduler_address(self):
        """reads scheduler host/port from dask.json file in the scheduler's working directory.
        Also reads dashboard port, if needed.
        """
        not self.debug or print("Reading scheduler host/port...")
        wd = self.scheduler_job.working_dir
        while True:
            json_file = wd.listdir().get("dask.json")
            if json_file is not None:
                break
            if JobStatus.FAILED == self.scheduler_job.status:
                raise OSError("Scheduler failed")
            time.sleep(2)
        dask_json = json.loads(json_file.raw().read())
        _h, _p = urlparse(dask_json["address"]).netloc.split(":")
        if self.connect_dashboard:
            try:
                self.dashboard_port = int(dask_json["services"]["dashboard"])
            except KeyError:
                self.connect_dask = False
        return _h, int(_p)

    def get_worker_job_description(self):
        """creates the JSON job description for starting a worker
        Returns JSON and optional array of input files
        """
        job = self.worker_job_desc
        if job.get("ApplicationName") is None and job.get("Executable") is None:
            job["ApplicationName"] = "dask-worker"
        args = job.get("Arguments", [])
        if "--scheduler-file" not in args:
            args.append("--scheduler-file")
            args.append("../%s/dask.json" % self.scheduler_job.job_id)
        if self.processes:
            args.append("--nworkers")
            args.append(str(self.processes))
        if self.threads:
            args.append("--nthreads")
            args.append(str(self.threads))
        job["Arguments"] = args
        resources = job.get("Resources", {})
        if self.queue is not None:
            resources["Queue"] = self.queue
        if self.project is not None:
            resources["Project"] = self.project
        if len(resources) > 0:
            job["Resources"] = resources
        return job, []

    def _submit_worker_job(self):
        """
        Starts and returns a worker job
        """
        job_desc, inputs = self.get_worker_job_description()
        worker = self.submitter.new_job(job_desc, inputs)
        not self.debug or print("Submitted worker job:", worker)
        return worker

    def scale(self, n=None, jobs=0, wait_for_startup=False):
        if n is not None:
            jobs = int(math.ceil(n / self.processes))
        while jobs < len(self.worker_jobs):
            self.worker_jobs.pop().abort()
        new_workers = []
        while jobs > len(self.worker_jobs):
            w = self._submit_worker_job()
            self.worker_jobs.append(w)
            new_workers.append(w)
        if wait_for_startup and len(new_workers) > 0:
            not self.debug or print("Waiting for worker(s) to start up...")
            for worker in new_workers:
                worker.poll(JobStatus.RUNNING)
                if JobStatus.FAILED == worker.status:
                    raise OSError("Worker %s failed: " % worker.resource_url)
        not self.debug or print("Worker(s) running.")

    def _start_forwarder(self):
        not self.debug or print("Starting port forwarder listening on port:", self.local_port)
        endpoint = self.scheduler_job.links["forwarding"]
        tr = self.scheduler_job.transport._clone()
        tr.use_security_sessions = False
        self.forwarder = Forwarder(
            tr,
            endpoint,
            service_port=self.scheduler_port,
            service_host=self.scheduler_host,
            login_node=None,
            debug=self.debug,
        )
        ctx = get_context("spawn")
        self.forwarding_process = ctx.Process(target=self.forwarder.run, args=[self.local_port])
        self.forwarding_process.start()
        if self.connect_dashboard:
            self.db_forwarder = Forwarder(
                tr,
                endpoint,
                service_port=self.dashboard_port,
                service_host=self.scheduler_host,
                login_node=None,
                debug=self.debug,
            )
            self.db_forwarding_process = ctx.Process(
                target=self.db_forwarder.run, args=[self.local_dashboard_port]
            )
            self.db_forwarding_process.start()

    def cleanup(self):
        if self.scheduler_job:
            self.scheduler_job.abort()
        for worker in self.worker_jobs:
            worker.abort()
        if self.forwarding_process:
            self.forwarding_process.kill()
        if self.db_forwarding_process:
            self.db_forwarding_process.kill()

    def close(self):
        self.cleanup()
        super().close()

    @property
    def dashboard_link(self):
        if self.connect_dashboard:
            return "localhost:%s" % str(self.local_dashboard_port)
        else:
            return None
