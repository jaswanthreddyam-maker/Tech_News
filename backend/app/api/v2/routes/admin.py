from fastapi import APIRouter, Depends

router = APIRouter(prefix="/admin", tags=["Operations Console"])

def get_current_admin():
    # Stub: Admin authentication ensures only privileged users can access read-only telemetry
    return "admin_user_123"

@router.get("/capabilities")
async def get_capabilities(admin: str = Depends(get_current_admin)):
    """
    Returns the Capability Registry metadata.
    Read-only API. No mutations.
    """
    # Mock capability registry dump
    return [
        {
            "name": "Planner",
            "version": "v1",
            "visibility": "internal",
            "health": "HEALTHY",
            "latency_ms": 120,
            "circuit_breaker": {"failure_threshold": 5},
            "timeouts": {"soft_ms": 5000, "hard_ms": 10000},
            "dependencies": ["KnowledgeGraph"]
        },
        {
            "name": "Research",
            "version": "v2",
            "visibility": "public",
            "health": "HEALTHY",
            "latency_ms": 450,
            "circuit_breaker": {"failure_threshold": 3},
            "timeouts": {"soft_ms": 15000, "hard_ms": 30000},
            "dependencies": ["WebSearch", "Memory"]
        }
    ]

@router.get("/goals")
async def get_goals(admin: str = Depends(get_current_admin)):
    """
    Exposes internal OS Goal states for tracing.
    Read-only API.
    """
    # Mock goals from OS database
    return [
        {
            "goal_id": "goal_1a2b3c",
            "owner_id": "enterprise_service_account",
            "state": "COMPLETED",
            "description": "Action: trigger_research. Target: quantum_computing.",
            "fingerprint": "abc123hash",
            "created_at": "2026-06-14T10:00:00Z"
        }
    ]

@router.get("/operations")
async def get_operations(admin: str = Depends(get_current_admin)):
    """
    Lists external Operations mapped to internal Goals.
    """
    # Mock operations from database
    return [
        {
            "operation_id": "op_9f8e7d",
            "status": "COMPLETED",
            "artifact_id": "art_112233",
            "message": "Research complete."
        }
    ]

@router.get("/replay/{goal_id}")
async def get_replay_trace(goal_id: str, admin: str = Depends(get_current_admin)):
    """
    Returns the flattened, sectioned execution trace for the Replay Explorer (ADR-0082).
    """
    # Mocking the deterministic trace response
    return {
        "metadata": {
            "goal_id": goal_id,
            "operation_id": "op_9f8e7d",
            "created_at": "2026-06-14T10:00:00Z",
            "duration_ms": 18200
        },
        "planner": {
            "strategy": "react",
            "latency_ms": 1200,
            "branches": ["branch_a", "branch_b"]
        },
        "workspace": {
            "initial_snapshot": "ws_100",
            "final_snapshot": "ws_105"
        },
        "branches": [
            {"branch_id": "branch_a", "name": "Research Path", "tasks": ["task_1"]},
            {"branch_id": "branch_b", "name": "Comparison Path", "tasks": ["task_2"]}
        ],
        "tasks": [
            {"task_id": "task_1", "capability": "Research", "status": "COMPLETED"},
            {"task_id": "task_2", "capability": "Comparison", "status": "COMPLETED"}
        ],
        "agents": [
            {"agent_id": "agent_worker_1", "task_id": "task_1"},
            {"agent_id": "agent_worker_2", "task_id": "task_2"}
        ],
        "capabilities": [
            {"capability": "Research", "latency_ms": 4500},
            {"capability": "Comparison", "latency_ms": 3200}
        ],
        "artifacts": [
            {"artifact_id": "art_112233", "type": "research_report", "status": "PUBLISHED"}
        ],
        "reflection": {
            "approved": True,
            "reasoning": "All evidence compiled successfully."
        },
        "evaluation": {
            "score": 92,
            "human_feedback": "Accepted",
            "configuration_version": "v17"
        }
    }

@router.get("/policies")
async def get_policies(admin: str = Depends(get_current_admin)):
    """
    Returns the active Policy Pipeline rules (ADR-0083).
    """
    # Mocking policy pipeline
    return {
        "pipeline": [
            {
                "id": "pol_auth",
                "name": "AuthenticationPolicy",
                "order": 1,
                "purpose": "Verifies valid enterprise identity",
                "decisions": 1420
            },
            {
                "id": "pol_budget",
                "name": "BudgetPolicy",
                "order": 2,
                "purpose": "Enforces workspace cost limits",
                "decisions": 1419
            },
            {
                "id": "pol_visibility",
                "name": "CapabilityVisibilityPolicy",
                "order": 3,
                "purpose": "Restricts capability access by visibility tier",
                "decisions": 1419
            },
            {
                "id": "pol_approval",
                "name": "OptimizationApprovalPolicy",
                "order": 4,
                "purpose": "Blocks optimizations exceeding concurrency limits",
                "decisions": 1419,
                "failure_reason": "Concurrency exceeds policy limit"
            }
        ]
    }

@router.get("/configurations")
async def get_configurations(admin: str = Depends(get_current_admin)):
    """
    Returns the history of system_configuration artifacts (ADR-0083).
    """
    # Mocking configuration history
    return [
        {
            "version": "v10",
            "status": "PENDING_APPROVAL",
            "author": "admin_user_123",
            "source_operation": "op_new_config",
            "created_at": "2026-06-14T12:00:00Z",
            "payload": {
                "max_agent_concurrency": 24,
                "planner_timeout_ms": 8000,
                "reflection_enabled": True,
                "lease_ttl": 600
            }
        },
        {
            "version": "v9",
            "status": "PUBLISHED",
            "author": "system",
            "source_operation": "op_baseline",
            "created_at": "2026-06-01T00:00:00Z",
            "payload": {
                "max_agent_concurrency": 16,
                "planner_timeout_ms": 10000,
                "reflection_enabled": False,
                "lease_ttl": 600
            }
        },
        {
            "version": "v8",
            "status": "SUPERSEDED",
            "author": "system",
            "source_operation": "op_init",
            "created_at": "2026-05-15T00:00:00Z",
            "payload": {
                "max_agent_concurrency": 8,
                "planner_timeout_ms": 15000,
                "reflection_enabled": False,
                "lease_ttl": 600
            }
        }
    ]

@router.get("/health")
async def get_health(admin: str = Depends(get_current_admin)):
    """
    Returns aggregated KPIs for Platform, Scheduler, Execution, and Governance.
    """
    return {
        "platform": {
            "status": "HEALTHY",
            "version": "v1.0",
            "configuration": "v18",
            "capabilities": "42/42"
        },
        "scheduler": {
            "queue_depth": 27,
            "running_goals": 14,
            "waiting_goals": 12,
            "retries": 1,
            "dead_letters": 0
        },
        "execution": {
            "average_latency_ms": 420,
            "artifacts_today": 1247,
            "replay_success_rate": 99.8,
            "planner_success_rate": 98.5
        },
        "governance": {
            "pending_approvals": 3,
            "published_config": "v18",
            "rejected_configs": 2,
            "policy_violations": 1
        }
    }

@router.get("/monitoring/scheduler")
async def get_scheduler_metrics(admin: str = Depends(get_current_admin)):
    """
    Returns detailed task queue metrics.
    """
    return {
        "queues": {
            "planning": {"depth": 3, "status": "HEALTHY"},
            "execution": {"depth": 18, "status": "HEALTHY"},
            "reflection": {"depth": 4, "status": "HEALTHY"},
            "evaluation": {"depth": 2, "status": "HEALTHY"}
        },
        "capabilities": [
            {
                "capability": "WebSearch",
                "latency_ms": 320,
                "availability": 99.9,
                "failure_rate": 0.01,
                "circuit_state": "CLOSED",
                "timeout_ms": 5000,
                "last_failure": None,
                "version": "v2"
            },
            {
                "capability": "ContentExtraction",
                "latency_ms": 1250,
                "availability": 98.5,
                "failure_rate": 0.05,
                "circuit_state": "HALF_OPEN",
                "timeout_ms": 15000,
                "last_failure": "2026-06-14T09:15:00Z",
                "version": "v1"
            }
        ],
        "recent_incidents": [
            {"type": "Capability Timeout", "time": "2026-06-14T09:15:00Z", "target": "ContentExtraction"},
            {"type": "Lease Expired", "time": "2026-06-14T09:18:00Z", "target": "Agent_Worker_2"},
            {"type": "Planner Retry", "time": "2026-06-14T09:21:00Z", "target": "Goal_1a2b3c"}
        ]
    }

@router.get("/monitoring/events")
async def get_live_events(admin: str = Depends(get_current_admin)):
    """
    Returns a stream of recent OS events.
    """
    return [
        {
            "id": "evt_1",
            "timestamp": "2026-06-14T09:17:00Z",
            "event": "Circuit Half Open",
            "severity": "WARNING",
            "target": "ContentExtraction",
            "link": "/ops/capabilities"
        },
        {
            "id": "evt_2",
            "timestamp": "2026-06-14T09:16:00Z",
            "event": "Reflection Finished",
            "severity": "INFO",
            "target": "Goal_1a2b3c",
            "link": "/ops/replay/goal_1a2b3c"
        },
        {
            "id": "evt_3",
            "timestamp": "2026-06-14T09:15:00Z",
            "event": "Artifact Published",
            "severity": "SUCCESS",
            "target": "art_112233",
            "link": "/ops/artifacts"
        },
        {
            "id": "evt_4",
            "timestamp": "2026-06-14T09:14:00Z",
            "event": "Goal Completed",
            "severity": "SUCCESS",
            "target": "Goal_1a2b3c",
            "link": "/ops/replay/goal_1a2b3c"
        }
    ]
