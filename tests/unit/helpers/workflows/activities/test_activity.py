from pyunicore.helpers.workflows.activities import activity


class TestStart:
    def test_to_dict(self):
        start = activity.Start(
            id="test-id",
        )
        expected = {
            "id": "test-id",
            "type": "START",
        }

        result = start.to_dict()

        assert result == expected


class TestSplit:
    def test_to_dict(self):
        split = activity.Split(
            id="test-id",
        )
        expected = {
            "id": "test-id",
            "type": "Split",
        }

        result = split.to_dict()

        assert result == expected


class TestBranch:
    def test_to_dict(self):
        branch = activity.Branch(
            id="test-id",
        )
        expected = {
            "id": "test-id",
            "type": "BRANCH",
        }

        result = branch.to_dict()

        assert result == expected


class TestMerge:
    def test_to_dict(self):
        merge = activity.Merge(
            id="test-id",
        )
        expected = {
            "id": "test-id",
            "type": "Merge",
        }

        result = merge.to_dict()

        assert result == expected


class TestSynchronize:
    def test_to_dict(self):
        synchronize = activity.Synchronize(
            id="test-id",
        )
        expected = {
            "id": "test-id",
            "type": "Synchronize",
        }

        result = synchronize.to_dict()

        assert result == expected


class TestHold:
    def test_to_dict(self):
        hold = activity.Hold(
            id="test-id",
        )
        expected = {
            "id": "test-id",
            "type": "HOLD",
        }

        result = hold.to_dict()

        assert result == expected
