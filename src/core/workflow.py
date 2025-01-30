"""
Workflow engine implementation for coordinating agent activities
Uses asyncio for concurrent operation management
"""
import asyncio
import logging
from typing import Dict, List, Any, Callable, Coroutine
from datetime import datetime

class WorkflowStep:
    """Represents a single step in a workflow"""
    def __init__(self, 
                 step_id: str, 
                 action: Callable[..., Coroutine[Any, Any, Any]],
                 requires: List[str] = None):
        self.step_id = step_id
        self.action = action
        self.requires = requires or []
        self.status = "pending"
        self.result = None
        self.error = None
        self.started_at = None
        self.completed_at = None

    async def execute(self, context: Dict[str, Any]) -> Any:
        """Execute the workflow step"""
        self.started_at = datetime.now()
        self.status = "running"
        try:
            self.result = await self.action(context)
            self.status = "completed"
        except Exception as e:
            self.status = "failed"
            self.error = str(e)
            raise
        finally:
            self.completed_at = datetime.now()
        return self.result

class Workflow:
    """Manages the execution of a sequence of workflow steps"""
    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self.steps: Dict[str, WorkflowStep] = {}
        self.context: Dict[str, Any] = {}
        self._logger = logging.getLogger(f"workflow.{workflow_id}")

    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow"""
        self.steps[step.step_id] = step

    async def execute(self) -> Dict[str, Any]:
        """Execute the entire workflow"""
        try:
            execution_order = self._determine_execution_order()
            for step_id in execution_order:
                step = self.steps[step_id]
                self._logger.info(f"Executing step: {step_id}")
                await step.execute(self.context)
            return self.context
        except Exception as e:
            self._logger.error(f"Workflow execution failed: {str(e)}")
            raise

    def _determine_execution_order(self) -> List[str]:
        """Determine the order of step execution based on dependencies"""
        executed = set()
        execution_order = []

        def can_execute(step: WorkflowStep) -> bool:
            return all(req in executed for req in step.requires)

        while len(executed) < len(self.steps):
            found_next = False
            for step_id, step in self.steps.items():
                if step_id not in executed and can_execute(step):
                    execution_order.append(step_id)
                    executed.add(step_id)
                    found_next = True
                    break
            if not found_next:
                raise ValueError("Circular dependency detected in workflow")

        return execution_order

class WorkflowEngine:
    """Manages multiple workflows and their execution"""
    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self._logger = logging.getLogger("workflow.engine")

    def create_workflow(self, workflow_id: str) -> Workflow:
        """Create a new workflow"""
        workflow = Workflow(workflow_id)
        self.workflows[workflow_id] = workflow
        return workflow

    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Execute a specific workflow"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        return await self.workflows[workflow_id].execute()

workflow_engine = WorkflowEngine()
