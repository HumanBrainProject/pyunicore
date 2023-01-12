""" Dask Distributed cluster implementation """
import json
import math
from multiprocessing import get_context
from urllib.parse import urlparse

from distributed.core import rpc
from distributed.core import Status
from distributed.deploy.cluster import Cluster

from pyunicore.client import JobStatus
from pyunicore.forwarder import Forwarder


class UNICORECluster(Cluster):
    """Deploy Dask on a HPC site via UNICORE"""

    def __init__(
        self,
        submitter,
        n_workers=0,
        name=None,
        asynchronous=False,
        queue=None,
        project=None,
        threads_per_process=None,
        processes_per_job=1,
        scheduler_options={},
        worker_options={},
        local_port=4322,
        debug=False,
        connection_timeout=60,
    ):
        super().__init__(asynchronous=asynchronous, name=name, quiet=not debug)
        self.submitter = submitter
        self.status = Status.created
        self.debug = debug
        self.local_port = local_port
        self.queue = queue
        self.project = project
        self.scheduler_options = scheduler_options
        self.worker_options = worker_options
        self.threads = threads_per_process
        self.processes = processes_per_job
        self.worker_jobs = []
        self.forwarding_process = None
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
                self.close()
            finally:
                raise
        self._loop_runner.start()
        self.sync(self._start)

    def get_scheduler_job_description(self):
        """creates the JSON job description for starting the scheduler
        Returns JSON and optional array of input files
        """
        job_start_scheduler = self.scheduler_options.get(
            "executable", {"ApplicationName": "dask-scheduler"}
        )
        self.scheduler_port = self.scheduler_options.get("port", 8786)
        self.scheduler_host = "localhost"
        job_start_scheduler["Arguments"] = [
            "--port",
            str(self.scheduler_port),
            "--scheduler-file",
            "./dask.json",
        ]
        additional_args = self.scheduler_options.get("additional_args", [])
        for arg in additional_args:
            job_start_scheduler["Arguments"].append(arg)
        resources = self.scheduler_options.get("Resources", {})
        if self.queue is not None:
            resources["Queue"] = self.queue
        if self.project is not None:
            resources["Project"] = self.project
        if len(resources) > 0:
            job_start_scheduler["Resources"] = resources
        return job_start_scheduler, []

    def _start_scheduler(self):
        """
        Starts the scheduler
        """
        job_desc, inputs = self.get_scheduler_job_description()
        job = self.submitter.new_job(job_desc, inputs)
        self.scheduler_job = job
        not self.debug or print("Submitted scheduler", job)
        not self.debug or print("Waiting for scheduler to start up...")

        job.poll(JobStatus.RUNNING)
        if JobStatus.FAILED == job.status:
            raise OSError("Launching scheduler failed")
        not self.debug or print("Scheduler is running.")
        if self.scheduler_port == 0 or not "ON_LOGIN_NODE" == job.properties["jobType"]:
            self.scheduler_host, self.scheduler_port = self._read_scheduler_address()

    def _read_scheduler_address(self):
        """reads scheduler host/port from dask.json file in the scheduler's working directory"""
        wd = self.scheduler_job.working_dir
        dask_json = json.loads(wd.stat("dask.json").raw().read())
        _h, _p = urlparse(dask_json["address"]).netloc.split(":")
        return _h, int(_p)

    def get_worker_job_description(self):
        """creates the JSON job description for starting a worker
        Returns JSON and optional array of input files
        """
        job_start_worker = self.worker_options.get("executable", {"ApplicationName": "dask-worker"})
        job_start_worker["Arguments"] = [
            "--scheduler-file",
            "../%s/dask.json" % self.scheduler_job.job_id,
        ]
        if self.processes:
            job_start_worker["Arguments"].append("--nworkers")
            job_start_worker["Arguments"].append(str(self.processes))
        if self.threads:
            job_start_worker["Arguments"].append("--nthreads")
            job_start_worker["Arguments"].append(str(self.threads))
        additional_args = self.worker_options.get("additional_args", [])
        for arg in additional_args:
            job_start_worker["Arguments"].append(arg)
        resources = self.worker_options.get("Resources", {})
        if self.queue is not None:
            resources["Queue"] = self.queue
        if self.project is not None:
            resources["Project"] = self.project
        if len(resources) > 0:
            job_start_worker["Resources"] = resources
        return job_start_worker, []

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
        if wait_for_startup:
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

    def close(self):
        if self.scheduler_job:
            self.scheduler_job.abort()
        for worker in self.worker_jobs:
            worker.abort()
        if self.forwarding_process:
            self.forwarding_process.kill()
        super().close()

    @property
    def dashboard_link(self):
        return None
