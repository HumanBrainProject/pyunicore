from typing import Dict

import dataclasses

from . import _api_object
from . import _dict_helper


@dataclasses.dataclass
class Resources(_api_object.ApiRequestObject):
    """Resources to request on the remote system.

    Args:
        runtime (str, optional): Job runtime (wall time).
            In seconds by default, append "min", "h", or "d" for other units.
        queue (str, default="batch"): Batch system queue/partition to use.
        nodes (int, default=1): Number of nodes.
        cpus (int, optional): Total number of CPUs.
        cpus_per_node (int, optional): Number of CPUs per node.
        memory (str, optional): Memory per node.
        reservation (str, optional): Batch system reservation ID.
        node_constraints (str, optional): Batch system node constraints.
        qos (str, optional): Batch system QoS.

    """

    runtime: str = None
    queue: str = "batch"
    nodes: int = 1
    cpus: int = None
    cpus_per_node: int = None
    memory: str = None
    reservation: str = None
    node_constraints: str = None
    qos: str = None

    def to_dict(self) -> Dict:
        """Return as dict."""
        key_values = {
            "Runtime": self.runtime,
            "Queue": self.queue,
            "Nodes": self.nodes,
            "CPUs": self.cpus,
            "CPUsPerNode": self.cpus_per_node,
            "Memory": self.memory,
            "Reservation": self.reservation,
            "NodeConstraints": self.node_constraints,
            "QoS": self.qos,
        }
        return _dict_helper.create_dict_with_not_none_values(**key_values)
