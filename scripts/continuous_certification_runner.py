#!/usr/bin/env python3
import os
import sys
import json
import uuid
import subprocess
import argparse
from datetime import datetime, timezone
from pathlib import Path
import httpx

BACKEND_DIR = Path(__file__).parent.parent / "backend"
RESULTS_DIR = BACKEND_DIR / "chaos" / "results" / "runtime"

def get_runner_version() -> str:
    return "1.0.0"

def clean_results_dir():
    if not RESULTS_DIR.exists():
        RESULTS_DIR.mkdir(parents=True)
    for file in RESULTS_DIR.glob("*.json"):
        file.unlink()

def run_pytest(cert_type: str) -> bool:
    print(f"Executing Chaos Suite for: {cert_type}")
    
    env = os.environ.copy()
    env["CHAOS_RUNNER"] = "0"
    env["PYTHONPATH"] = str(BACKEND_DIR)
    
    cmd = [sys.executable, "-m", "pytest", "-v", "tests/chaos/test_runtime_certification.py"]
    
    if cert_type == "NIGHTLY":
        cmd.extend(["-m", "nightly"])
    elif cert_type == "WEEKLY":
        cmd.extend(["-m", "weekly"])
    elif cert_type == "MANUAL":
        pass # run all
    
    result = subprocess.run(cmd, cwd=str(BACKEND_DIR), env=env)
    return result.returncode == 0

def gather_evidence() -> list:
    evidence_list = []
    if not RESULTS_DIR.exists():
        return evidence_list
        
    for file in RESULTS_DIR.glob("*.json"):
        with open(file, "r") as f:
            data = json.load(f)
            evidence_list.append(data)
            
    return evidence_list

def submit_to_backend(payload: dict):
    # In a real environment, this URL would be parameterized and use an API key
    url = "http://localhost:8000/api/v1/certification/runs"
    try:
        response = httpx.post(url, json=payload, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        print(f"✅ Successfully submitted CertificationRun! Grade: {data.get('grade')}")
    except httpx.HTTPError as e:
        print(f"❌ Failed to submit CertificationRun: {e}")
        if hasattr(e, 'response') and e.response:
            print(e.response.text)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Continuous Certification Runner")
    parser.add_argument("--type", choices=["NIGHTLY", "WEEKLY", "MANUAL", "PRE_RELEASE"], default="MANUAL")
    args = parser.parse_args()
    
    cert_type = args.type
    run_id = f"CERT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    started_at = datetime.now(timezone.utc)
    
    clean_results_dir()
    
    # 1. Execute Chaos Tests
    run_pytest(cert_type)
    
    completed_at = datetime.now(timezone.utc)
    
    # 2. Gather Evidence
    evidences = gather_evidence()
    
    # 3. Construct Payload
    payload = {
        "run_id": run_id,
        "certification_type": cert_type,
        "certification_runner_version": get_runner_version(),
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "evidences": evidences
    }
    
    # 4. Submit to Backend Service (which handles grading and persistence)
    submit_to_backend(payload)

if __name__ == "__main__":
    main()
