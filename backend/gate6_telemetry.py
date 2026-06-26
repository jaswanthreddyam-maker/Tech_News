import asyncio
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.user import AIJobHistory

async def run_telemetry_check():
    async with AsyncSessionLocal() as db:
        # Get overall metrics
        stmt = select(
            AIJobHistory.task_type,
            func.count(AIJobHistory.id).label('total_runs'),
            func.avg(AIJobHistory.latency_ms).label('avg_latency'),
            func.avg(AIJobHistory.total_tokens).label('avg_tokens'),
            func.avg(AIJobHistory.cost_usd).label('avg_cost'),
            func.sum(AIJobHistory.cost_usd).label('total_cost')
        ).group_by(AIJobHistory.task_type)
        
        result = await db.execute(stmt)
        rows = result.all()
        
        print("=== GATE 6: AI Cost & Latency Certification ===")
        print(f"{'Task Type':<15} | {'Runs':<5} | {'Avg Latency (ms)':<17} | {'Avg Tokens':<12} | {'Avg Cost ($)':<12} | {'Total Cost ($)':<12}")
        print("-" * 85)
        
        for row in rows:
            task_type = row.task_type or "UNKNOWN"
            runs = row.total_runs
            avg_lat = float(row.avg_latency) if row.avg_latency else 0.0
            avg_tok = float(row.avg_tokens) if row.avg_tokens else 0.0
            avg_cost = float(row.avg_cost) if row.avg_cost else 0.0
            total_cost = float(row.total_cost) if row.total_cost else 0.0
            
            print(f"{task_type:<15} | {runs:<5} | {avg_lat:<17.2f} | {avg_tok:<12.2f} | ${avg_cost:<11.5f} | ${total_cost:<11.5f}")
        
        print("\nProjected daily operational cost (100 articles/day):")
        for row in rows:
            if float(row.total_runs) > 0:
                avg_cost = float(row.avg_cost) if row.avg_cost else 0.0
                print(f" - {row.task_type}: ${avg_cost * 100:.2f}/day")
                
        print("\nCertification Complete.")

if __name__ == "__main__":
    asyncio.run(run_telemetry_check())
