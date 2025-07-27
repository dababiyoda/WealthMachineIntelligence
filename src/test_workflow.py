"""
Test workflow to verify the core functionality
"""
import asyncio
import logging
import sys
import pytest

from core.workflow import WorkflowEngine, WorkflowStep
from core.knowledge_graph import KnowledgeGraph, Node, Edge
from agents.base import BaseAgent

# Configure logging to output to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_workflow():
    # Initialize components
    logger.info("Initializing workflow components...")
    workflow_engine = WorkflowEngine()
    knowledge_graph = KnowledgeGraph()

    # Create a test agent
    logger.info("Creating test agent...")
    test_agent = BaseAgent("test-1", "test-agent")
    await test_agent.initialize()

    # Create a simple workflow
    logger.info("Creating test workflow...")
    workflow = workflow_engine.create_workflow("test-workflow")

    # Add test steps
    async def step1(context):
        logger.info("Executing step 1: Creating test node 1")
        node = Node("test-node-1", "test", {"name": "Test Node 1"})
        knowledge_graph.add_node(node)
        context['node1'] = node
        return True

    async def step2(context):
        logger.info("Executing step 2: Creating test node 2 and edge")
        node = Node("test-node-2", "test", {"name": "Test Node 2"})
        knowledge_graph.add_node(node)
        edge = Edge("test-node-1", "test-node-2", "relates_to", {})
        knowledge_graph.add_edge(edge)
        return True

    workflow.add_step(WorkflowStep("create-node-1", step1))
    workflow.add_step(WorkflowStep("create-node-2", step2, requires=["create-node-1"]))

    # Execute workflow
    try:
        logger.info("Starting workflow execution...")
        result = await workflow_engine.execute_workflow("test-workflow")
        logger.info("Workflow executed successfully")

        # Verify results
        nodes = knowledge_graph.get_nodes_by_type("test")
        logger.info(f"Created {len(nodes)} nodes")

        neighbors = knowledge_graph.get_neighbors("test-node-1")
        logger.info(f"Node 1 has {len(neighbors)} neighbors")

    except Exception as e:
        logger.error(f"Workflow execution failed: {str(e)}")
        raise

if __name__ == "__main__":
    logger.info("Starting test workflow script")
    asyncio.run(test_workflow())
    logger.info("Test workflow script completed")