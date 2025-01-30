"""
Base agent implementation for the multi-agent AI architecture
Provides core functionality for agent lifecycle management
"""

class BaseAgent:
    """Foundation class for all agents in the system"""
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.state = "initialized"
        self.knowledge_base = {}
    
    def initialize(self):
        """Initialize agent resources and connections"""
        self.state = "active"
    
    def process_event(self, event):
        """Process incoming events and update agent state"""
        pass
    
    def shutdown(self):
        """Clean shutdown of agent resources"""
        self.state = "shutdown"
