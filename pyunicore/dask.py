""" Dask Distributed cluster implementation """
from multiprocessing import get_context

from distributed.core import rpc
from distributed.core import Status
from distributed.deploy.cluster import Cluster

from pyunicore.client import JobStatus
from pyunicore.forwarder import Forwarder


class UNICORECluster(Cluster):
    """Deploy Dask on a HPC site via UNICORE"""

    def __init__(
        self,
        unicore_client,
        n_workers=0,
        name=None,
        asynchronous=False,
        scheduler_options={},
        worker_options={},
        local_port=4322,
        debug=False,
    ):
        super().__init__(asynchronous=asynchronous, name=name, quiet=not debug)
        self.unicore_client = unicore_client
        self.status = Status.created
        self.debug = debug
        self.local_port = local_port
        self.scheduler_options = scheduler_options
        self.worker_options = worker_options
        self.worker_jobs = []
        self.forwarding_process = None
        try:
            self._start_scheduler()
            self._start_forwarder()
            self.scheduler_comm = rpc("tcp://localhost:%s" % self.local_port)
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

    def _start_scheduler(self):
        """
        Starts the scheduler
        """
        self.scheduler_port = self.scheduler_options.get("port", 8786)
        self.scheduler_host = "localhost"
        job_start_scheduler = {
            "Executable": "dask-scheduler",
            "Arguments": [
                "--host",
                "localhost",
                "--port %s" % self.scheduler_port,
                "--scheduler-file",
                "./dask.json",
            ],
        }
        job = self.unicore_client.new_job(job_start_scheduler)
        self.scheduler_job = job
        not self.debug or print("Submitted scheduler", job)
        not self.debug or print("Waiting for scheduler to start up...")

        job.poll(JobStatus.RUNNING)
        if JobStatus.FAILED == job.status:
            raise OSError("Launching scheduler failed")
        not self.debug or print("Scheduler is running.")

    def _start_worker(self):
        """
        Starts a worker and returns the corresponding UNICORE job
        """

        job_start_worker = {
            "Executable": "dask-worker",
            "Arguments": ["--scheduler-file", "../%s/dask.json" % self.scheduler_job.job_id],
        }
        worker = self.unicore_client.new_job(job_start_worker)
        not self.debug or print("Submitted worker:", worker)
        return worker

    def scale(self, n_workers):
        while n_workers < len(self.worker_jobs):
            self.worker_jobs.pop().abort()
        while n_workers > len(self.worker_jobs):
            self.worker_jobs.append(self._start_worker())

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

    def shutdown(self, status="SUCCEEDED", diagnostics=None):
        self.close()

    @property
    def dashboard_link(self):
        return None
