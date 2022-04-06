"""Represents the job description of the UNICORE REST API.

See https://sourceforge.net/p/unicore/wiki/Job_Description/

"""
from typing import Dict
from typing import List

import dataclasses

from . import _api_object
from . import data
from . import resources as resources_


@dataclasses.dataclass
class JobDescription(_api_object.ApiRequestObject):
    """UNICORE's job description for submitting jobs.

    :param application_name: Application name.
    :param application_version: Application version.
    :param executable: Command line.
    :param arguments: Command line arguments.
    :param environment: Environment values.
    :param parameters: Application parameters.
    :param stdout: Filename for the standard output (default: "stdout").
    :param stderr: Filename for the standard error (default: "stderr").
    :param stdin: Filename for the standard input (optional).
    :param ignore_non_zero_exit_code: Don't fail the job if app exits with non-zero exit code (default: false).
    :param user_precommand: Pre-processing.
    :param run_user_precommand_on_login_node: Pre-processing is done on login node (default: true).
    :param user_precommand_ignore_non_zero_exit_code: Don't fail job if pre-command fails (default: false).
    :param user_postommand: Post-processing.
    :param run_user_postcommand_on_login_node: Post-processing is done on login node (default: true).
    :param user_postcommand_ignore_non_zero_exit_code: Don't fail job if post-command fails (default: false).
    :param resources: The job's resource requests.
    :param project: Accounting project.
    :param imports: Stage-in / data import.
    :param exports: Stage-out / data export.
    :param have_client_stage_in: Tell the server that the client does / does not want to send any additional files.
    :param job_type: 'normal', 'interactive', 'raw' 	Whether to run the job via the batch system ('normal', default) or on a login node ('interactive'), or as a batch job but with a user-specified file containing the batch system directives.
    :param login_node: For 'interactive' jobs, select a login node (by name, as configured server side. Wildcards '*' and '?' can be used).
    :param bss_file: For 'raw' jobs, specify the relative or absolute file name of a file containing batch system directives. UNICORE will append the user executable..
    :param tags: Job tags.
    :param notification: URL to send job status change notifications to (via HTTP POST).
    :param user_email: User email to send notifications to (if the batch system supports it).
    :param name: Job name.
    """

    executable: str
    project: str
    Resources: resources_.Resources = dataclasses.field(
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
            raise ValueError("If job type is 'raw', BSS file has to be specified")

    def to_dict(self) -> Dict:
        pass
