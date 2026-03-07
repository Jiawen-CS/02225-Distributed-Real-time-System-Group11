from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Link:
    id: str
    source: str
    destination: str
    bandwidth_mbps: float
    delay: float # microseconds

@dataclass
class Node:
    id: str
    ports: int
    outgoing_links: Dict[int, Link] = field(default_factory=dict)

@dataclass
class Stream:
    id: int
    source: str
    destinations: List[str]
    size: int # bytes
    period: float # microseconds
    pcp: int
    deadline: float # microseconds

@dataclass
class Route:
    flow_id: int
    path: List[Dict[str, Any]] # List of {node: id, port: port}

@dataclass
class Frame:
    id: int
    stream_id: int
    size: int
    creation_time: float
    priority: int
    path_index: int = 0
    # Stats
    start_time: float = 0.0
    end_time: float = 0.0
