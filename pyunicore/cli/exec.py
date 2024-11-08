from __future__ import annotations

import json

from pyunicore.cli.base import Base
from pyunicore.client import Client
from pyunicore.client import Job
from pyunicore.client import JobStatus


class JobExecutionBase(Base):
    """Base class for job execution commands"""

    def add_command_args(self):
        self.parser.add_argument("-s", "--sitename", required=False, type=str, help="Site name")
        self.parser.add_argument(
            "-S", "--server-url", required=False, type=str, help="Server URL to submit to"
        )
        self.parser.add_argument(
            "-a",
            "--asynchronous",
            required=False,
            action="store_true",
            help="Just submit, don't wait for finish",
        )
        self.parser.add_argument(
            "-d",
            "--dry-run",
            required=False,
            action="store_true",
            help="Dry run, do not submit the job",
        )
        self.parser.add_argument(
            "-T",
            "--tags",
            required=False,
            help="Tag the job with the given tag(s) (comma-separated)",
        )

    def get_group(self):
        return "Job execution"

    def get_site_client(self):
        if self.args.sitename:
            if self.registry:
                try:
                    site_client = self.registry.site(self.args.sitename)
                except KeyError:
                    raise ValueError("Site '%s' not found in registry." % self.args.sitename)
            else:
                raise ValueError(
                    "Sitename resolution requires registry - please check your configuration!"
                )
        elif not self.args.server_url:
            raise ValueError("Either --server-url or --sitename must be given.")
        else:
            site_client = Client(self.credential, site_url=self.args.server_url)
        return site_client

    def run_job(self, job_definition, submission_endpoint):
        job = submission_endpoint.new_job(job_definition)
        self.verbose("Submitted job: %s" % job.resource_url)
        if not self.args.asynchronous:
            self.verbose("Waiting for job to finish ...")
            job.poll()
        return job

    def fetch_output(self, job: Job):
        try:
            self.verbose(f"{job.status}, exit code {job.properties['exitCode']}")
        except KeyError:
            self.verbose(job.status)
        print("*** Command output\n")
        with job.working_dir.stat("stdout").raw() as f:
            print(str(f.read(), "UTF-8"))
        print("*** End of command output.")
        print("*** Error output\n")
        with job.working_dir.stat("stderr").raw() as f:
            print(str(f.read(), "UTF-8"))
        print("*** End of error output.")


class Exec(JobExecutionBase):
    """Execute a non batch command (i.e. on a login node)"""

    def add_command_args(self):
        super().add_command_args()
        self.parser.prog = "unicore exec"
        self.parser.description = self.get_synopsis()
        self.parser.add_argument("commands", help="Command(s) to run", nargs="*")
        self.parser.add_argument(
            "-L", "--login-node", required=False, type=str, help="Login node to use"
        )
        self.parser.add_argument(
            "-Q", "--keep", required=False, action="store_true", help="Don't remove finished job"
        )

    def get_synopsis(self):
        return """Runs a command through UNICORE. The command will not be run through a
           remote queue, but on the cluster login node. The command and
           its arguments are taken from the command line. The client will wait
           for the job to finish and print standard output and error to
           the console."""

    def get_description(self):
        return "run a command through UNICORE"

    def build_job(self) -> dict:
        job_definition = {"Job type": "ON_LOGIN_NODE"}
        if self.args.login_node:
            job_definition["Login node"] = self.args.login_node
        if len(self.args.commands) > 0:
            job_definition["Executable"] = self.args.commands[0]
        if len(self.args.commands) > 1:
            job_definition["Arguments"] = self.args.commands[1:]
        if self.args.tags:
            job_definition["Tags"] = self.args.tags.split(",")
        self.verbose(json.dumps(job_definition, indent=2))
        return job_definition

    def run(self, args):
        super().setup(args)
        site_client = self.get_site_client()
        self.verbose("Submission endpoint: %s" % site_client.resource_url)
        jd = self.build_job()
        if self.args.dry_run:
            self.verbose("Dry run, not submitting anything.")
            return
        job = self.run_job(jd, site_client)
        if not self.args.asynchronous:
            self.fetch_output(job)
            if not self.args.keep:
                job.delete()


class Run(JobExecutionBase):
    """Run a UNICORE job"""

    def add_command_args(self):
        super().add_command_args()
        self.parser.prog = "unicore run"
        self.parser.description = self.get_synopsis()
        self.parser.add_argument("jobs", help="Job file(s) to run", nargs="*")

    def get_synopsis(self):
        return """Runs job(s) through UNICORE. The job definition(s) are read from <jobs> or
           stdin. A job can be executed in two modes. In the default synchronous mode, UCC
           will wait for the job to finish. In asynchonous mode, initiated
           by the 'a' option, the job will be submitted and started."""

    def get_description(self):
        return "runs job(s) through UNICORE"

    def build_job(self, jobfile=None) -> dict:
        with open(jobfile) as f:
            job_definition = json.load(f)
        if self.args.tags:
            job_definition["Tags"] = self.args.tags.split(",")
        self.verbose(json.dumps(job_definition, indent=2))
        return job_definition

    def run(self, args):
        super().setup(args)
        site_client = self.get_site_client()
        self.verbose("Submission endpoint: %s" % site_client.resource_url)

        if len(self.args.jobs) > 0:
            for jobfile in self.args.jobs:
                self.verbose("Reading job from <%s>" % jobfile)
                jd = self.build_job(jobfile)
                if self.args.dry_run:
                    self.verbose("Dry run, not submitting anything.")
                    continue
                else:
                    job = self.run_job(jd, site_client)
                    if not self.args.asynchronous:
                        self.fetch_output(job)


class ListJobs(Base):
    """List UNICORE jobs"""

    def add_command_args(self):
        self.parser.prog = "unicore list-jobs"
        self.parser.description = self.get_synopsis()
        self.parser.add_argument("-s", "--sitename", required=False, type=str, help="Site name")
        self.parser.add_argument(
            "-l", "--long", required=False, action="store_true", help="Detailed output"
        )
        self.parser.add_argument(
            "-T",
            "--tags",
            required=False,
            help="Tag the job with the given tag(s) (comma-separated)",
        )

    def get_synopsis(self):
        return """Lists your jobs per site. The list can be limited to a single
           site specified using the '-s' option."""

    def get_description(self):
        return "list your jobs"

    def get_group(self):
        return "Job execution"

    __f = " {:>24s} | {:>10s} | {:s} "

    def details(self, job: Job):
        print(self.__f.format(job.properties["submissionTime"], job.status, job.resource_url))

    def print_header(self):
        print(self.__f.format("Submitted", "Status", "URL"))
        print(" -------------------------|------------|----------------")

    def run(self, args):
        super().setup(args)
        tags = self.args.tags.split(",") if self.args.tags is not None else []
        if not self.registry:
            raise ValueError("Registry required - please check your configuration!")
        if self.args.long:
            self.print_header()
        for endpoint in self.registry.site_urls.values():
            site_client = Client(self.credential, site_url=endpoint)
            for job in site_client.get_jobs(tags=tags):
                if self.args.long:
                    self.details(job)
                else:
                    print(job.resource_url)


class CancelJob(Base):
    """Cancel a UNICORE job"""

    def add_command_args(self):
        self.parser.prog = "unicore cancel-job"
        self.parser.description = self.get_synopsis()
        self.parser.add_argument("job_url", help="Job URL(s)", nargs="*")

    def get_synopsis(self):
        return """Cancels UNICORE job(s)."""

    def get_description(self):
        return "cancel job(s)"

    def get_group(self):
        return "Job execution"

    def run(self, args):
        super().setup(args)
        for endpoint in self.args.job_url:
            self.verbose("Cancelling: %s" % endpoint)
            Job(self.credential, job_url=endpoint).abort()


class GetJobStatus(Base):
    """Get the status of a UNICORE job. Also, allow to wait for the job to reach
    a certain state.
    """

    def add_command_args(self):
        self.parser.prog = "unicore job-status"
        self.parser.description = self.get_synopsis()
        self.parser.add_argument("job_url", help="Job URL(s)", nargs="*")
        self.parser.add_argument(
            "-w",
            "--wait-for",
            required=False,
            help="Wait for the given job status (STAGINGIN, QUEUED, RUNNING, "
            "STAGINGOUT, SUCCESSFUL)",
        )
        self.parser.add_argument(
            "-t",
            "--timeout",
            required=False,
            type=int,
            default=0,
            help="Timeout for job status polling",
        )
        self.parser.add_argument(
            "-l", "--long", required=False, action="store_true", help="More detailed job status"
        )
        self.parser.add_argument(
            "-a", "--all", required=False, action="store_true", help="Full details (including log)"
        )

    def get_synopsis(self):
        return """Gets the status of UNICORE job(s)."""

    def get_description(self):
        return "get job status"

    def get_group(self):
        return "Job execution"

    def run(self, args):
        super().setup(args)
        for endpoint in self.args.job_url:
            job = Job(self.credential, job_url=endpoint)
            if self.args.wait_for is not None:
                s = JobStatus(self.args.wait_for)
                if self.args.timeout > 0:
                    t = "(timeout: %s sec.)" % self.args.timeout
                else:
                    t = ""
                self.verbose(f"Waiting for job to be {s} ... {t}")
                job.poll(state=s, timeout=self.args.timeout)
            else:
                self.show_status(job)

    def show_status(self, job):
        s = f"{job.resource_url} {job.status}"
        if job.status.ordinal() >= JobStatus.SUCCESSFUL.ordinal():
            s = f"{s} exit code: {job.properties['exitCode']}"
        print(s)
        if self.args.long or self.args.all:
            print("  Working directory:", job.properties["_links"]["workingDirectory"]["href"])
            jt = job.properties["jobType"]
            print("  Job type:         ", jt)
            if jt != "ON_LOGIN_NODE":
                print("  Queue:            ", job.properties.get("queue", "n/a"))
        if self.args.all:
            for log in job.properties["log"]:
                print("  Log:", log)


class JobWrapper:

    def __init__(self, job: dict):
        self.job = job
        self.local_imports = []
