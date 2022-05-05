import pyunicore.helpers.requests.job_description as job_description
import pyunicore.helpers.requests.resources as resources


class TestJobDescription:
    def test_to_dict(self):
        res = resources.Resources(nodes=2)
        job = job_description.JobDescription(
            executable="test-executable",
            project="test-project",
            resources=res,
        )
        expected = {
            "Executable": "test-executable",
            "IgnoreNonZeroExitCode": "false",
            "Job type": "normal",
            "Project": "test-project",
            "Resources": {"Nodes": 2, "Queue": "batch"},
            "RunUserPostcommandOnLoginNode": "true",
            "RunUserPrecommandOnLoginNode": "true",
            "Stderr": "stderr",
            "Stdout": "stdout",
            "UserPostcommandIgnoreNonZeroExitcode": "false",
            "UserPrecommandIgnoreNonZeroExitcode": "false",
            "haveClientStageIn": "false",
        }

        result = job.to_dict()

        assert result == expected
