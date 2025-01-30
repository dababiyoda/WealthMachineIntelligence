"""
Base agent implementation for the multi-agent AI architecture
Provides core functionality for agent lifecycle management
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

class AgentState:
    """Enumeration of possible agent states"""
    INITIALIZED = "initialized"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"

class BaseAgent:
    """Foundation class for all agents in the system"""
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.state = AgentState.INITIALIZED
        self.knowledge_base: Dict[str, Any] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.last_updated = datetime.now()
        self._logger = logging.getLogger(f"agent.{agent_type}.{agent_id}")

    async def initialize(self) -> None:
        """Initialize agent resources and connections"""
        try:
            await self._setup_resources()
            self.state = AgentState.ACTIVE
            self._logger.info(f"Agent {self.agent_id} initialized successfully")
        except Exception as e:
            self.state = AgentState.ERROR
            self._logger.error(f"Failed to initialize agent: {str(e)}")
            raise

    async def _setup_resources(self) -> None:
        """Setup agent-specific resources"""
        pass

    async def process_event(self, event: Dict[str, Any]) -> None:
        """Process incoming events and update agent state"""
        try:
            await self.event_queue.put(event)
            self._logger.debug(f"Event queued: {json.dumps(event)}")
        except Exception as e:
            self._logger.error(f"Failed to process event: {str(e)}")
            raise

    async def run(self) -> None:
        """Main agent execution loop"""
        while self.state == AgentState.ACTIVE:
            try:
                event = await self.event_queue.get()
                await self._handle_event(event)
                self.last_updated = datetime.now()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in agent execution: {str(e)}")
                self.state = AgentState.ERROR

    async def _handle_event(self, event: Dict[str, Any]) -> None:
        """Handle specific event types"""
        event_type = event.get('type')
        if event_type == 'shutdown':
            await self.shutdown()
        elif event_type == 'pause':
            self.state = AgentState.PAUSED
        elif event_type == 'resume':
            self.state = AgentState.ACTIVE

    async def shutdown(self) -> None:
        """Clean shutdown of agent resources"""
        self._logger.info(f"Shutting down agent {self.agent_id}")
        self.state = AgentState.SHUTDOWN

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            'agent_id': self.agent_id,
            'type': self.agent_type,
            'state': self.state,
            'last_updated': self.last_updated.isoformat(),
            'queue_size': self.event_queue.qsize()
        }