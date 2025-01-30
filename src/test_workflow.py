"""
Test workflow to verify the core functionality
"""
import asyncio
import logging
from core.workflow import WorkflowEngine, WorkflowStep
from core.knowledge_graph import KnowledgeGraph, Node, Edge
from agents.base import BaseAgent

logging.basicConfig(level=logging.INFO)

async def test_workflow():
    # Initialize components
    workflow_engine = WorkflowEngine()
    knowledge_graph = KnowledgeGraph()
    
    # Create a test agent
    test_agent = BaseAgent("test-1", "test-agent")
    await test_agent.initialize()
    
    # Create a simple workflow
    workflow = workflow_engine.create_workflow("test-workflow")
    
    # Add test steps
    async def step1(context):
        node = Node("test-node-1", "test", {"name": "Test Node 1"})
        knowledge_graph.add_node(node)
        context['node1'] = node
        return True
        
    async def step2(context):
        node = Node("test-node-2", "test", {"name": "Test Node 2"})
        knowledge_graph.add_node(node)
        edge = Edge("test-node-1", "test-node-2", "relates_to", {})
        knowledge_graph.add_edge(edge)
        return True
    
    workflow.add_step(WorkflowStep("create-node-1", step1))
    workflow.add_step(WorkflowStep("create-node-2", step2, requires=["create-node-1"]))
    
    # Execute workflow
    try:
        result = await workflow_engine.execute_workflow("test-workflow")
        print("Workflow executed successfully")
        
        # Verify results
        nodes = knowledge_graph.get_nodes_by_type("test")
        print(f"Created {len(nodes)} nodes")
        
        neighbors = knowledge_graph.get_neighbors("test-node-1")
        print(f"Node 1 has {len(neighbors)} neighbors")
        
    except Exception as e:
        print(f"Workflow execution failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_workflow())
