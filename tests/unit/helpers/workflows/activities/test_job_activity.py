from pyunicore.helpers.workflows.activities import job
from pyunicore.helpers import jobs


class TestJob:
    def test_to_dict(self):
        user_preferences = job.UserPreferences(
            role="test-role",
            uid="test-uid",
            group="test-group",
            supplementary_groups="test-groups",
        )
        options = [job.Option.IgnoreFailure(True), job.Option.MaxResubmits(2)]
        description = jobs.Description(
            executable="test-executable",
            project="test-project",
        )
        job_ = job.Job(
            id="test-id",
            description=description,
            site_name="test-site",
            user_preferences=user_preferences,
            options=options,
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
                "User preferences": {
                    "role": "test-role",
                    "uid": "test-uid",
                    "group": "test-group",
                    "supplementaryGroups": "test-groups",
                },
            },
            "options": {"IGNORE_FAILURE": "true", "MAX_RESUBMITS": 2},
        }

        result = job_.to_dict()

        assert result == expected
