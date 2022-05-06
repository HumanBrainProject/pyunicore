import pyunicore.helpers.jobs.description as description
import pyunicore.helpers.jobs.resources as resources


class TestJobDescription:
    def test_to_dict(self):
        res = resources.Resources(nodes=2)
        job = description.Description(
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
