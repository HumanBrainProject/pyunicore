import dataclasses
from typing import Dict
from typing import Optional

from pyunicore.helpers import _api_object


@dataclasses.dataclass
class Resources(_api_object.ApiRequestObject):
    """Resources to request on the remote system.

    Args:
        runtime (str, optional): Job runtime (wall time).
            In seconds by default, append "min", "h", or "d" for other units.
        queue (str, optional): Batch system queue/partition to use.
        nodes (int, optional): Number of nodes.
        cpus (int, optional): Total number of CPUs.
        cpus_per_node (int, optional): Number of CPUs per node.
        memory (str, optional): Memory per node.
        reservation (str, optional): Batch system reservation ID.
        node_constraints (str, optional): Batch system node constraints.
        qos (str, optional): Batch system QoS.

    """

    runtime: Optional[str] = None
    queue: Optional[str] = None
    nodes: Optional[int] = None
    cpus: Optional[int] = None
    cpus_per_node: Optional[int] = None
    memory: Optional[str] = None
    reservation: Optional[str] = None
    node_constraints: Optional[str] = None
    qos: Optional[str] = None

    def _to_dict(self) -> Dict:
        return {
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
