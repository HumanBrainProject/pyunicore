""" Exec and related commands """

import json

from pyunicore.cli.base import Base
from pyunicore.client import Client
from pyunicore.client import Job


class Exec(Base):
    def add_command_args(self):
        self.parser.prog = "unicore exec"
        self.parser.description = self.get_synopsis()
        self.parser.add_argument("commands", help="Command(s) to run", nargs="*")
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
            "-L",
            "--login-node",
            required=False,
            type=str,
            help="Login node to use",
        )
        self.parser.add_argument(
            "-T",
            "--tags",
            required=False,
            help="Tag the job with the given tag(s) (comma-separated)",
        )
        self.parser.add_argument(
            "-Q", "--keep", required=False, action="store_true", help="Don't remove finished job"
        )

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

    def build_job(self):
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

    def run_job(self, job_definition, submission_endpoint):
        job = submission_endpoint.new_job(job_definition)
        self.verbose("Submitted job: %s" % job.resource_url)
        if not self.args.asynchronous:
            self.verbose("Waiting for job to finish ...")
            job.poll()
        return job

    def get_output(self, job: Job):
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

    def get_synopsis(self):
        return """Runs a command through UNICORE. The command will not be run through a
           remote queue, but on the cluster login node. The command and
           its arguments are taken from the command line. The client will wait
           for the job to finish and print standard output and error to
           the console."""

    def run(self, args):
        super().run(args)
        site_client = self.get_site_client()
        self.verbose("Submission endpoint: %s" % site_client.resource_url)
        jd = self.build_job()
        if self.args.dry_run:
            self.verbose("Dry run, not submitting anything.")
            return
        job = self.run_job(jd, site_client)
        if not self.args.asynchronous:
            self.get_output(job)
        if not self.args.keep:
            job.delete()
