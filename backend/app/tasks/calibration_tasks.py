import asyncio
import os
import logging
from pathlib import Path
from app.services.analytics.calibration_service import CalibrationAnalyticsService

logger = logging.getLogger(__name__)

async def run_calibration_report_generation():
    """
    Executes the calibration analytics service and saves the output to calibration_report.md
    """
    logger.info("Starting Calibration Analytics Sprint Report Generation...")
    service = CalibrationAnalyticsService()
    
    report_markdown = await service.generate_report()
    
    # Save the report to the project root
    root_dir = Path(__file__).parent.parent.parent.parent
    report_path = root_dir / "calibration_report.md"
    
    with open(report_path, "w") as f:
        f.write(report_markdown)
        
    logger.info(f"Calibration report successfully generated at {report_path}")

if __name__ == "__main__":
    asyncio.run(run_calibration_report_generation())
