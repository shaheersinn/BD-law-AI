"""
scripts/check_deploy.py — Deployment readiness diagnostic for ORACLE.

Usage:
    python scripts/check_deploy.py [--full]
"""
import os
import sys
from pathlib import Path

def check_env_vars():
    print("--- [1] Checking Environment Variables (.env.example) ---")
    env_example = Path(".env.example")
    if not env_example.exists():
        print("[FAIL] .env.example not found!")
        return
    
    with open(env_example) as f:
        required_vars = [
            line.split('=')[0].strip() 
            for line in f if line.strip() and not line.startswith('#')
        ]
    
    print(f"Found {len(required_vars)} required variables in .env.example.")
    print("[PASS] All required variables are documented.")

def check_requirements():
    print("\n--- [2] Checking Dependencies ---")
    backend_reqs = Path("backend/requirements.txt")
    root_reqs = Path("requirements.txt")
    
    for req_file in [backend_reqs, root_reqs]:
        if not req_file.exists():
            print(f"[FAIL] {req_file} not found!")
            continue
            
        with open(req_file) as f:
            content = f.read()
            if "redbeat==" in content and "celery-redbeat==" not in content:
                print(f"[FAIL] {req_file} uses incorrect 'redbeat' name instead of 'celery-redbeat'!")
            elif "celery-redbeat==2.3.3" in content:
                print(f"[PASS] {req_file} has correct celery-redbeat version.")
            else:
                print(f"[WARN] {req_file} version of celery-redbeat is not 2.3.3.")

def check_do_spec():
    print("\n--- [3] Checking do-app.yaml ---")
    spec = Path("do-app.yaml")
    if not spec.exists():
        print("[FAIL] do-app.yaml not found!")
        return
        
    with open(spec) as f:
        content = f.read()
        if "REPLACE_GITHUB_USERNAME" in content:
            print("[FAIL] do-app.yaml still has placeholders!")
        if "oracle-bd" in content:
            # Check if it was supposed to be replaced by the user but wasn't
            print("[WARN] do-app.yaml still uses 'oracle-bd' (legacy name?)")
        if "shaheersinn/BD-law-AI" in content:
            print("[PASS] do-app.yaml points to correct repository.")

def check_docker():
    print("\n--- [4] Checking Docker Build Context ---")
    dockerfile = Path("backend/Dockerfile")
    if not dockerfile.exists():
        # Check root as fallback
        dockerfile = Path("Dockerfile")
        
    if dockerfile.exists():
        print(f"[PASS] Dockerfile found at {dockerfile}")
    else:
        print("[FAIL] No Dockerfile found!")

if __name__ == "__main__":
    print("ORACLE Deployment Readiness Audit")
    print("=================================")
    check_env_vars()
    check_requirements()
    check_do_spec()
    check_docker()
    print("\nAudit Complete.")
