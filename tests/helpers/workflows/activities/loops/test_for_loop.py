import pytest

from pyunicore.helpers.workflows.activities import loops
from pyunicore.helpers.workflows import variable


class TestChunking:
    def test_chunksize_and_chunking_formula_given(self):
        with pytest.raises(ValueError):
            loops.Chunking(
                chunksize=3,
                type=loops.ChunkingType.Normal,
                chunksize_formula="if(TOTAL_SIZE>50*1024)return 5*1024 else return 2048;",  # noqa
            )


class TestFor:
    @pytest.mark.parametrize(
        ("range", "chunking", "expected_range", "expected_chunking"),
        [
            # Test case: values used for iteration.
            (loops.Values([1, 2, 3]), None, {"values": [1, 2, 3]}, None),
            # Test case: Normal chunking with size 3.
            (
                loops.Values([1, 2, 3]),
                loops.Chunking(
                    chunksize=3,
                    type=loops.ChunkingType.Normal,
                ),
                {"values": [1, 2, 3]},
                {
                    "chunksize": 3,
                    "type": "NORMAL",
                },
            ),
            # Test case: Size chunking with size 3 kbytes.
            (
                loops.Values([1, 2, 3]),
                loops.Chunking(
                    chunksize=3,
                    type=loops.ChunkingType.Size,
                ),
                {"values": [1, 2, 3]},
                {
                    "chunksize": 3,
                    "type": "SIZE",
                },
            ),
            # Test case: Normal chunking with size 3 and filename format.
            (
                loops.Values([1, 2, 3]),
                loops.Chunking(
                    chunksize=3,
                    type=loops.ChunkingType.Normal,
                    filename_format="file_{0}.pdf",
                ),
                {"values": [1, 2, 3]},
                {
                    "chunksize": 3,
                    "type": "NORMAL",
                    "filename_format": "file_{0}.pdf",
                },
            ),
            # Test case: Size with chunksize formula.
            (
                loops.Values([1, 2, 3]),
                loops.Chunking(
                    type=loops.ChunkingType.Size,
                    chunksize_formula="if(TOTAL_SIZE>50*1024)return 5*1024 else return 2048;",  # noqa
                ),
                {"values": [1, 2, 3]},
                {
                    "type": "SIZE",
                    "chunksize_formula": "if(TOTAL_SIZE>50*1024)return 5*1024 else return 2048;",  # noqa
                },
            ),
            # Test case: Variables used for iteration.
            (
                loops.Variables(
                    [
                        loops.Variable(
                            name="x",
                            type=variable.VariableType.Integer,
                            initial_value=1,
                            expression="x++",
                            end_condition="x<2",
                        )
                    ]
                ),
                None,
                {
                    "variables": [
                        {
                            "variable_name": "x",
                            "type": "INTEGER",
                            "start_value": 1,
                            "expression": "x++",
                            "end_condition": "x<2",
                        }
                    ]
                },
                None,
            ),
            # Test case: Files used for iteration.
            (
                loops.Files(
                    [
                        loops.File(
                            base="https://mysite/rest/core/storages/my_storage/files/pdf/",  # noqa
                            include=["*.pdf"],
                            exclude=[
                                "unused1.pdf",
                                "unused2.pdf",
                            ],
                            recurse=True,
                            indirection=True,
                        )
                    ]
                ),
                None,
                {
                    "file_sets": [
                        {
                            "base": "https://mysite/rest/core/storages/my_storage/files/pdf/",  # noqa
                            "include": ["*.pdf"],
                            "exclude": [
                                "unused1.pdf",
                                "unused2.pdf",
                            ],
                            "recurse": "true",
                            "indirection": "true",
                        }
                    ]
                },
                None,
            ),
        ],
    )
    def test_to_dict(
        self,
        loop_body,
        expected_loop_body,
        range,
        chunking,
        expected_range,
        expected_chunking,
    ):
        loop = loops.ForEach(
            id="test-for-each-loop-id",
            body=loop_body,
            iterator_name="test-name",
            range=range,
            chunking=chunking,
        )

        expected = {
            "id": "test-for-each-loop-id",
            "type": "FOR_EACH",
            "iterator_name": "test-name",
            **expected_range,
            "body": expected_loop_body,
        }

        if chunking is not None:
            expected["chunking"] = expected_chunking

        result = loop.to_dict()

        assert result == expected
