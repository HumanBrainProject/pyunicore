import pytest

import pyunicore.helpers.requests.data as data


class TestCredentials:
    def test_to_dict(self):
        credentials = data.Credentials("user", "password")
        expected = {
            "Username": "user",
            "Password": "password",
        }

        result = credentials.to_dict()

        assert result == expected


class TestImport:
    @pytest.mark.parametrize(
        ("import_", "expected"),
        [
            (
                data.Import(
                    from_="here",
                    to="there",
                ),
                {"From": "here", "To": "there", "FailOnError": "true"},
            ),
            (
                data.Import(
                    from_="here",
                    to="there",
                    fail_on_error=False,
                ),
                {"From": "here", "To": "there", "FailOnError": "false"},
            ),
            (
                data.Import(
                    from_="here",
                    to="there",
                    data="test",
                ),
                {
                    "From": "here",
                    "To": "there",
                    "FailOnError": "true",
                    "Data": "test",
                },
            ),
            (
                data.Import(
                    from_="here",
                    to="there",
                    credentials=data.Credentials("user", "password"),
                ),
                {
                    "From": "here",
                    "To": "there",
                    "FailOnError": "true",
                    "Credentials": {"Username": "user", "Password": "password"},
                },
            ),
        ],
    )
    def test_to_dict(self, import_, expected):
        result = import_.to_dict()

        assert result == expected


class TestExport:
    def test_to_dict(self):
        export_ = data.Export(
            from_="there",
            to="here",
        )
        expected = {"From": "there", "To": "here"}

        result = export_.to_dict()

        assert result == expected
