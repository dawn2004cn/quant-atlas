"""Shared-Memory Hyper-Grid — Phase 17.
mmap-based global memory pool over global_state_bus for microsecond sync."""

from __future__ import annotations

import json
import mmap
import os
import struct
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.core.mesh.global_state_bus import get_global_state_bus

logger = get_logger(__name__)


@dataclass
class GridNode:
    """A node in the shared memory grid."""
    node_id: str
    memory_offset: int
    memory_size: int
    cpu_cores: float
    last_heartbeat: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class GridMessage:
    """Inter-node message via shared memory."""
    sender: str
    receiver: str
    message_type: str
    payload: Any
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SharedMemoryHyperGrid:
    """Distributed shared memory grid using mmap and global_state_bus."""
    
    def __init__(self, grid_size_mb: int = 1024):
        self._grid_size = grid_size_mb * 1024 * 1024
        self._grid_path = Path(__file__).resolve().parents[3] / "instance" / "hyper_grid.bin"
        self._grid_path.parent.mkdir(parents=True, exist_ok=True)
        self._grid_path.touch()
        self._mmap = None
        self._nodes: dict[str, GridNode] = {}
        self._lock = threading.RLock()
        self._bus = get_global_state_bus()
        self._broadcast_area = 0  # Reserved offset 0 for broadcast messages
        self._init_grid()
    
    def _init_grid(self):
        """Initialize shared memory file and mmap."""
        if self._grid_path.stat().st_size < self._grid_size:
            with open(self._grid_path, "wb") as f:
                f.seek(self._grid_size - 1)
                f.write(b"\x00")

        # Windows needs O_BINARY mode for mmap compatibility
        import os as _os
        fd = _os.open(self._grid_path, _os.O_RDWR, _os.O_BINARY)
        try:
            self._mmap = mmap.mmap(fd, self._grid_size, access=mmap.ACCESS_READ | mmap.ACCESS_WRITE)
        except Exception:
            _os.close(fd)
            raise
        logger.info("Hyper-Grid initialized: %d MB", self._grid_size // 1024 // 1024)
    
    def register_node(self, node_id: str, memory_mb: int = 64, cpu_cores: float = 1.0) -> GridNode:
        """Register a new node in the grid."""
        with self._lock:
            if node_id in self._nodes:
                return self._nodes[node_id]
            
            # Find free memory slot
            offset = self._find_free_slot(memory_mb * 1024 * 1024)
            if offset is None:
                raise MemoryError("No free memory slot in Hyper-Grid")
            
            node = GridNode(
                node_id=node_id,
                memory_offset=offset,
                memory_size=memory_mb * 1024 * 1024,
                cpu_cores=cpu_cores,
                last_heartbeat=datetime.now(timezone.utc).isoformat(),
            )
            self._nodes[node_id] = node
            
            # Register to global bus for cross-process sync
            self._bus.write_state(f"hyper_grid.{node_id}", {
                "node_id": node_id,
                "offset": offset,
                "size": node.memory_size,
                "cpu": cpu_cores,
                "status": "active",
            })
            
            logger.info("Node %s registered in Hyper-Grid at offset %d MB", node_id, offset // 1024 // 1024)
            return node
    
    def _find_free_slot(self, required_size: int) -> int | None:
        """Find a free memory slot of given size."""
        used = sorted([n.memory_offset + n.memory_size for n in self._nodes.values()])
        if not used:
            return 0
        
        # Check before first block
        if used[0] >= required_size:
            return 0
        
        # Check between blocks
        for i in range(1, len(used)):
            free_start = used[i - 1]
            free_end = used[i]
            if free_end - free_start >= required_size:
                return free_start
        
        # Check after last block
        if self._grid_size - used[-1] >= required_size:
            return used[-1]
        
        return None
    
    def write_memory(self, node_id: str, offset: int, data: bytes) -> bool:
        """Write data to shared memory."""
        # Broadcast area is a special zone at offset 0
        if node_id == "broadcast":
            try:
                self._mmap[self._broadcast_area : self._broadcast_area + len(data)] = data
                return True
            except Exception as exc:
                logger.warning("Hyper-Grid broadcast write failed: %s", exc)
                return False

        node = self._nodes.get(node_id)
        if not node:
            return False

        if offset < 0 or offset + len(data) > node.memory_size:
            return False

        try:
            self._mmap[node.memory_offset + offset : node.memory_offset + offset + len(data)] = data
            return True
        except Exception as exc:
            logger.warning("Hyper-Grid write failed: %s", exc)
            return False
    
    def read_memory(self, node_id: str, offset: int, size: int) -> bytes | None:
        """Read data from shared memory."""
        node = self._nodes.get(node_id)
        if not node:
            return None
        
        if offset < 0 or offset + size > node.memory_size:
            return None
        
        try:
            return self._mmap[node.memory_offset + offset : node.memory_offset + offset + size]
        except Exception as exc:
            logger.warning("Hyper-Grid read failed: %s", exc)
            return None
    
    def broadcast_message(self, sender: str, message_type: str, payload: Any):
        """Broadcast a message to all nodes."""
        msg = GridMessage(
            sender=sender,
            receiver="*",
            message_type=message_type,
            payload=payload,
        )
        data = json.dumps(msg.__dict__).encode("utf-8")
        
        # Write to broadcast area
        self.write_memory("broadcast", 0, data)
        
        # Sync via global bus
        self._bus.write_state(f"hyper_grid.broadcast", {
            "sender": sender,
            "type": message_type,
            "timestamp": msg.timestamp,
        })
    
    def sync_all(self) -> dict[str, Any]:
        """Sync all node states."""
        with self._lock:
            return {node_id: {
                "node_id": node.node_id,
                "memory_size": node.memory_size,
                "cpu_cores": node.cpu_cores,
                "last_heartbeat": node.last_heartbeat,
            } for node_id, node in self._nodes.items()}
    
    def cleanup(self):
        """Cleanup shared memory."""
        if self._mmap:
            try:
                self._mmap.close()
            except Exception:
                logger.warning("Suppressed exception", exc_info=True)
                pass
        logger.info("Hyper-Grid cleaned up")
