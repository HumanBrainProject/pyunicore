from typing import Dict

import dataclasses

from . import _api_object
from . import _dict_helper


@dataclasses.dataclass
class Resources(_api_object.ApiRequestObject):
    """Resources to request on the remote system.

    :param runtime: Job runtime (wall time).
                    (in seconds, append "min", "h", or "d" for other units).
    :param queue: Batch system queue/partition to use.
                  Defaults to `"batch"`.
    :param nodes: Number of nodes.
                  Defaults to `1`.
    :param cpus: Total number of CPUs.
    :param cpus_per_node: Number of CPUs per node.
    :param memory: Memory per node.
    :param reservation: Batch system reservation ID.
    :param node_constraints: Batch system node constraints.
    :param qos:	Batch system QoS.
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
