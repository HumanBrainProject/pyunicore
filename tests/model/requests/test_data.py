import pyunicore.model.requests.data as data


class TestCredentials:
    def test_to_dict(self):
        credentials = data.Credentials("user", "password")
        expected = {
            "Username": "user",
            "Password": "password",
        }

        result = credentials.to_dict()

        assert result == expected
