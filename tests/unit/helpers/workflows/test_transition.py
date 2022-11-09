from pyunicore.helpers.workflows import transition


class TestTransition:
    def test_to_dict(self):
        transition_ = transition.Transition(
            from_="here",
            to="there",
            condition="test-condition",
        )
        expected = {
            "from": "here",
            "to": "there",
            "condition": "test-condition",
        }

        result = transition_.to_dict()

        assert result == expected
