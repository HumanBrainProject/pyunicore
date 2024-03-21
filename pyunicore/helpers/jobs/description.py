import dataclasses
from typing import Dict
from typing import List
from typing import Optional

from pyunicore.helpers import _api_object
from pyunicore.helpers.jobs import data
from pyunicore.helpers.jobs import resources as _resources


@dataclasses.dataclass
class Description(_api_object.ApiRequestObject):
    """UNICORE's job description for submitting jobs.

    Args:
        executable (str, optional) : Command line.
        project (str, optional): Accounting project.
        resources (Resources, optional): The job's resource requests.
        application_name (str, optional): Application name.
        application_version (str, optional): Application version.
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
        imports (list[Import], optional): Stage-in / data import.
        exports (list[Export], optional): Stage-out / data export.
        have_client_stage_in (bool, default=False): Tell the server that the
            client does / does not want to send any additional files.
        job_type (str, default="batch): 'batch', 'on_login_node', 'raw', 'allocate'
            Whether to run the job via the batch system ('batch', default) or
            on a login node ('interactive'), or as a batch job but with a
            user-specified file containing the batch system directives ('raw').
            The 'allocate' job type will only create an allocation,
            without running anything.
        login_node (str, optional): For jobs of the 'on_login_node' type, select
            a login node (by name, as configured server side.
            Wildcards '*' and '?' can be used).
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

    executable: Optional[str] = None
    project: Optional[str] = None
    resources: Optional[_resources.Resources] = dataclasses.field(
        default_factory=_resources.Resources
    )
    application_name: Optional[str] = None
    application_version: Optional[str] = None
    arguments: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    parameters: Optional[Dict[str, str]] = None
    stdout: Optional[str] = "stdout"
    stderr: Optional[str] = "stderr"
    stdin: Optional[str] = None
    ignore_non_zero_exit_code: Optional[bool] = False
    user_precommand: Optional[str] = None
    run_user_precommand_on_login_node: Optional[bool] = True
    user_precommand_ignore_non_zero_exitcode: Optional[bool] = False
    user_postcommand: Optional[str] = None
    run_user_postcommand_on_login_node: Optional[bool] = True
    user_postcommand_ignore_non_zero_exit_code: Optional[bool] = False
    imports: Optional[List[data.Import]] = None
    exports: Optional[List[data.Export]] = None
    have_client_stage_in: Optional[bool] = False
    job_type: Optional[str] = "normal"
    login_node: Optional[str] = None
    bss_file: Optional[str] = None
    tags: Optional[List[str]] = None
    notification: Optional[str] = None
    user_email: Optional[str] = None
    name: Optional[str] = None

    def __post_init__(self):
        """Set `have_client_stage_in=True` if any files have to be imported."""
        if self.imports:
            self.have_client_stage_in = True

        if self.job_type == "raw" and self.bss_file is None:
            raise ValueError("If job type is 'raw', BSS file has to be specified")

    def _to_dict(self) -> Dict:
        return {
            "ApplicationName": self.application_name,
            "ApplicationVersion": self.application_version,
            "Executable": self.executable,
            "Arguments": self.arguments,
            "Environment": self.environment,
            "Parameters": self.parameters,
            "Stdout": self.stdout,
            "Stderr": self.stderr,
            "Stdin": self.stdin,
            "IgnoreNonZeroExitCode": self.ignore_non_zero_exit_code,
            "User precommand": self.user_precommand,
            "RunUserPrecommandOnLoginNode": (self.run_user_precommand_on_login_node),
            "UserPrecommandIgnoreNonZeroExitcode": (self.user_precommand_ignore_non_zero_exitcode),
            "User postcommand": self.user_postcommand,
            "RunUserPostcommandOnLoginNode": (self.run_user_postcommand_on_login_node),
            "UserPostcommandIgnoreNonZeroExitcode": (
                self.user_postcommand_ignore_non_zero_exit_code
            ),
            "Project": self.project,
            "Resources": self.resources,
            "Imports": self.imports,
            "Exports": self.exports,
            "haveClientStageIn": self.have_client_stage_in,
            "Job type": self.job_type,
            "Login node": self.login_node,
            "BSS file": self.bss_file,
            "Tags": self.tags,
            "Notification": self.notification,
            "User email": self.user_email,
            "Name": self.name,
        }
