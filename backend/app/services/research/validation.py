import logging
from typing import Any

logger = logging.getLogger(__name__)

class ExecutionValidationFailed(Exception):
    pass

class ExecutionValidation:
    """
    Validates that the ExecutionGraph (DAG) completed successfully and produced sufficient evidence.
    Enforces ADR-0026: Evidence Before Synthesis.
    """
    def __init__(self):
        pass

    def validate(self, execution_results: dict[str, Any]) -> bool:
        """
        Validates the results of the DAG.
        If any provider failed, or sufficient evidence was not found, raises an exception.
        """
        logger.info("ExecutionValidation: Validating DAG execution results.")

        # Check for explicitly failed tasks
        for task_name, result in execution_results.items():
            if isinstance(result, Exception):
                logger.error(f"ExecutionValidation: Task {task_name} failed. Halting synthesis.")
                raise ExecutionValidationFailed(f"Task {task_name} failed: {result!s}")

        # Check if we have sufficient evidence (prototype logic)
        has_evidence = any(result for result in execution_results.values() if result)

        if not has_evidence:
            logger.error("ExecutionValidation: Insufficient evidence retrieved. ADR-0026 violation prevented.")
            raise ExecutionValidationFailed("Insufficient evidence to synthesize an answer.")

        logger.info("ExecutionValidation: DAG results validated successfully.")
        return True
