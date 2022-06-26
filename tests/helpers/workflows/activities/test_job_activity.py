from pyunicore.helpers.workflows.activities import job
from pyunicore.helpers import jobs


class TestJob:
    def test_to_dict(self):
        description = jobs.Description(
            executable="test-executable",
            project="test-project",
        )
        job_ = job.Job(
            id="test-id",
            description=description,
            site_name="test-site",
        )
        expected = {
            "id": "test-id",
            "type": "JOB",
            "job": {
                "Executable": "test-executable",
                "IgnoreNonZeroExitCode": "false",
                "Job type": "normal",
                "Project": "test-project",
                "Resources": {"Nodes": 1, "Queue": "batch"},
                "RunUserPostcommandOnLoginNode": "true",
                "RunUserPrecommandOnLoginNode": "true",
                "Site name": "test-site",
                "Stderr": "stderr",
                "Stdout": "stdout",
                "UserPostcommandIgnoreNonZeroExitcode": "false",
                "UserPrecommandIgnoreNonZeroExitcode": "false",
                "haveClientStageIn": "false",
            },
        }

        result = job_.to_dict()

        assert result == expected
