import dataclasses

from pyunicore.helpers.workflows.activities.loops import while_loop


@dataclasses.dataclass
class RepeatUntil(while_loop.While):
    """A repeat-until-loop-like activity within a workflow."""

    def _type(self) -> str:
        return "REPEAT_UNTIL"
