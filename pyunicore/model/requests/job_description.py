"""Represents the job description of the UNICORE REST API.

See https://sourceforge.net/p/unicore/wiki/Job_Description/

"""
from typing import Dict
from typing import List
from typing import Optional

import dataclasses

from . import _api_object
from . import data
from . import resources


@dataclasses.dataclass
class JobDescription(_api_object.ApiRequestObject):
    """UNICORE's job description for submitting jobs.

    ApplicationName 	String 	Application name
    ApplicationVersion 	String 	Application version
    Executable 	String 	Command line
    Arguments 	List of strings 	Command line arguments
    Environment 	Map of strings 	Environment values
    Parameters 	Map 	Application parameters
    Stdout 	String 	Filename for the standard output (default: "stdout")
    Stderr 	String 	Filename for the standard error (default: "stderr")
    Stdin 	String 	Filename for the standard input (optional)
    IgnoreNonZeroExitCode 	"true" / "false" 	Don't fail the job if app exits with non-zero exit code (default: false)
    User precommand 	String 	Pre-processing
    RunUserPrecommandOnLoginNode 	"true"/"false" 	Pre-processing is done on login node (default: true)
    UserPrecommandIgnoreNonZeroExitCode 	"true"/"false" 	Don't fail job if pre-command fails (default: false)
    User postcommand 	String 	Post-processing
    RunUserPostcommandOnLoginNode 	"true" / "false" 	Post-processing is done on login node (default: true)
    UserPostcommandIgnoreNonZeroExitCode 	"true"/"false" 	Don't fail job if post-command fails (default: false)
    Resources 	Map 	The job's resource requests
    Project 	String 	Accounting project
    Imports 	List of imports 	Stage-in / data import
    Exports 	List of exports 	Stage-out / data export
    haveClientStageIn 	"true" / "false" 	Tell the server that the client does / does not want to send any additional files
    Job type 	'normal', 'interactive', 'raw' 	Whether to run the job via the batch system ('normal', default) or on a login node ('interactive'), or as a batch job but with a user-specified file containing the batch system directives
    Login node 	String 	For 'interactive' jobs, select a login node (by name, as configured server side. Wildcards '*' and '?' can be used)
    BSS file 	String 	For 'raw' jobs, specify the relative or absolute file name of a file containing batch system directives. UNICORE will append the user executable.
    Tags 	List of strings 	Job tags
    Notification 	String 	URL to send job status change notifications to (via HTTP POST)
    User email 	String 	User email to send notifications to (if the batch system supports it)
    Name 	String 	Job name
    """
    executable: str
    Project: str
    Resources: resources.Resources = dataclasses.field(default_factory=resources.Resources)
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

