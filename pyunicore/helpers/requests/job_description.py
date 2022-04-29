"""Represents the job description of the UNICORE REST API.

See https://sourceforge.net/p/unicore/wiki/Job_Description/

"""
import dataclasses
from typing import Dict
from typing import List

from . import _api_object
from . import data
from . import resources as resources_


@dataclasses.dataclass
class JobDescription(_api_object.ApiRequestObject):
    """UNICORE's job description for submitting jobs.

    Args:
        application_name (str, optional): Application name.
        application_version (str, optional): Application version.
        executable (str) : Command line.
        arguments (list[str], optional): Command line arguments.
        environment (dict[str, str], optinal): Environment values.
        parameters (str, optional): Application parameters.
        stdout (str, default="stdout"): Filename for the standard output.
        stderr (str, default="stderr"): Filename for the standard error.
        stdin (str, optional): Filename for the standard input.
        ignore_non_zero_exit_code (bool, default=False): Don't fail the job if
            app exits with non-zero exit code.
        user_precommand (str, optional): Pre-processing.
        run_user_precommand_on_login_node (bool, default=True): Pre-processing
            is done on login node.
        user_precommand_ignore_non_zero_exit_code (bool, default=False): Don't
            fail job if pre-command fails.
        user_postommandFalse: Post-processing.
        run_user_postcommand_on_login_node (bool, default=True): Post-processing
            is done on login node.
        user_postcommand_ignore_non_zero_exit_code (bool, default=False): Don't
            fail job if post-command fails.
        resources (Resources): The job's resource requests.
        project (str): Accounting project.
        imports (list[Import], optional): Stage-in / data import.
        exports (list[Export], optional): Stage-out / data export.
        have_client_stage_in (bool, default=False): Tell the server that the
            client does / does not want to send any additional files.
        job_type (str, default="normal): 'normal', 'interactive', 'raw'
            Whether to run the job via the batch system ('normal', default) or
            on a login node ('interactive'), or as a batch job but with a
            user-specified file containing the batch system directives.
        login_node (str, optional): For 'interactive' jobs, select a login node
            (by name, as configured server side. Wildcards '*' and '?' can be
            used).
        bss_file (str, optional): For 'raw' jobs, specify the relative or
            absolute file name of a file containing batch system directives.
            UNICORE will append the user executable.
        tags (list[str], optional): Job tags.
        notification (str, optional): URL to send job status change
            notifications to. Will be sent via HTTP POST.
        user_email (str, optional): User email to send notifications to
            Only works if the batch system supports it.
        name (str, optional): Job name.
    """

    executable: str
    project: str
    resources: resources_.Resources = dataclasses.field(
        default_factory=resources_.Resources
    )
    application_name: str = None
    application_version: str = None
    arguments: List[str] = None
    environment: Dict[str, str] = None
    parameters: Dict[str, str] = None
    stdout: str = "stdout"
    stderr: str = "stderr"
    stdin: str = None
    ignore_non_zero_exit_code: bool = False
    user_precommand: str = None
    run_user_precommand_on_login_node: bool = True
    user_precommand_ignore_non_zero_exitcode: bool = False
    user_postcommand: str = None
    run_user_postcommand_on_login_node: bool = True
    user_postcommand_ignore_non_zero_exit_code: bool = False
    imports: List[data.Import] = None
    exports: List[data.Export] = None
    have_client_stage_in: bool = False
    job_type: str = "normal"
    login_node: str = None
    bss_file: str = None
    tags: List[str] = None
    notification: str = None
    user_email: str = None
    name: str = None

    def __post_init__(self):
        """Set `have_client_stage_in=True` if any files have to be imported."""
        if self.imports:
            self.have_client_stage_in = True

        if self.job_type == "raw" and self.bss_file is None:
            raise ValueError(
                "If job type is 'raw', BSS file has to be specified"
            )

    def to_dict(self) -> Dict:
        pass
