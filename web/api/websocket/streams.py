"""
WebSocket Stream Manager for BOT_Trading v3.0

Manages real-time data streams for WebSocket connections.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class StreamManager:
    """
    Manages WebSocket data streams.
    
    Provides real-time data streaming for:
    - Trader updates
    - Trade executions
    - System metrics
    - Market data
    """
    
    def __init__(self):
        """Initialize StreamManager."""
        self.active_streams: Dict[str, Set[str]] = {}
        self.stream_data: Dict[str, Any] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        logger.info("StreamManager initialized")
    
    async def start(self):
        """Start stream manager."""
        self._running = True
        logger.info("StreamManager started")
    
    async def stop(self):
        """Stop stream manager and cleanup."""
        self._running = False
        
        # Cancel all running tasks
        for task_id, task in self._tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self._tasks.clear()
        self.active_streams.clear()
        self.stream_data.clear()
        logger.info("StreamManager stopped")
    
    async def subscribe(self, client_id: str, stream_type: str) -> bool:
        """
        Subscribe client to a stream.
        
        Args:
            client_id: Client identifier
            stream_type: Type of stream to subscribe to
            
        Returns:
            Success status
        """
        if stream_type not in self.active_streams:
            self.active_streams[stream_type] = set()
        
        self.active_streams[stream_type].add(client_id)
        logger.debug(f"Client {client_id} subscribed to {stream_type}")
        return True
    
    async def unsubscribe(self, client_id: str, stream_type: str) -> bool:
        """
        Unsubscribe client from a stream.
        
        Args:
            client_id: Client identifier
            stream_type: Type of stream to unsubscribe from
            
        Returns:
            Success status
        """
        if stream_type in self.active_streams:
            self.active_streams[stream_type].discard(client_id)
            logger.debug(f"Client {client_id} unsubscribed from {stream_type}")
            return True
        return False
    
    async def get_stream_data(self, stream_type: str) -> Optional[Dict[str, Any]]:
        """
        Get current data for a stream.
        
        Args:
            stream_type: Type of stream
            
        Returns:
            Stream data or None
        """
        return self.stream_data.get(stream_type)
    
    async def update_stream(self, stream_type: str, data: Dict[str, Any]):
        """
        Update stream data.
        
        Args:
            stream_type: Type of stream
            data: New data for the stream
        """
        self.stream_data[stream_type] = {
            **data,
            "timestamp": datetime.utcnow().isoformat()
        }
        logger.debug(f"Updated {stream_type} stream with new data")
    
    def get_subscribers(self, stream_type: str) -> Set[str]:
        """
        Get all subscribers for a stream type.
        
        Args:
            stream_type: Type of stream
            
        Returns:
            Set of client IDs
        """
        return self.active_streams.get(stream_type, set())
    
    def get_active_streams(self) -> Dict[str, int]:
        """
        Get information about active streams.
        
        Returns:
            Dictionary with stream types and subscriber counts
        """
        return {
            stream_type: len(subscribers)
            for stream_type, subscribers in self.active_streams.items()
        }