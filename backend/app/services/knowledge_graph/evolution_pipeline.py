import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge_graph.alias_resolver import AliasResolver
from app.services.knowledge_graph.audit_suite import GraphAuditSuite
from app.services.knowledge_graph.confidence_engine import ConfidenceEngine
from app.services.knowledge_graph.conflict_resolver import ConflictResolver
from app.services.knowledge_graph.duplicate_detector import DuplicateDetector
from app.services.knowledge_graph.merge_engine import MergeEngine
from app.services.knowledge_graph.repair_planner import RepairPlanner

logger = logging.getLogger(__name__)

class EvolutionPipeline:
    """
    Orchestrates the Knowledge Graph Evolution processes.
    """
    def __init__(self):
        self.alias_resolver = AliasResolver()
        self.duplicate_detector = DuplicateDetector()
        self.merge_engine = MergeEngine()
        self.conflict_resolver = ConflictResolver()
        self.confidence_engine = ConfidenceEngine()
        self.audit_suite = GraphAuditSuite()
        self.repair_planner = RepairPlanner()

    async def evolve_node(self, session: AsyncSession, node_id: str) -> None:
        """
        Runs the evolution pipeline for a specific node when it is updated or ingested.
        """
        logger.info(f"EvolutionPipeline: Starting evolution for node {node_id}")

        # 1. Duplicate Detection
        candidates = await self.duplicate_detector.detect_duplicates(session, node_id)

        # 2. Merge Proposals/Execution
        for candidate in candidates:
            await self.merge_engine.process_candidate(session, candidate)

        # Context building for confidence could happen here
        base_confidence = self.confidence_engine.calculate_base_confidence({})

        logger.info(f"EvolutionPipeline: Completed evolution for node {node_id}")

    async def run_system_audit(self, session: AsyncSession) -> None:
        """
        Runs the full consistency audit and generates repair plans.
        """
        logger.info("EvolutionPipeline: Running full system audit")
        findings = self.audit_suite.run_all({})

        if findings:
            await self.repair_planner.generate_plan(session, findings)
