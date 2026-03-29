import sys
import os
import asyncio
from datetime import datetime, UTC

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

async def validate_all():
    print("=" * 60)
    print(f"ORACLE PRE-LAUNCH VALIDATION - {datetime.now(UTC).isoformat()}")
    print("=" * 60)

    checks = []

    # 1. Scraper Registry Check
    try:
        from app.scrapers.registry import ScraperRegistry
        count = ScraperRegistry.count()
        print(f"[*] Scraper Registry: {count} scrapers registered.")
        if count < 110:
            print(f"[!] WARNING: Registered scrapers ({count}) is below target (110+).")
            checks.append(("scrapers_count", False))
        else:
            checks.append(("scrapers_count", True))
    except Exception as e:
        print(f"[X] Scraper Registry failure: {e}")
        checks.append(("scrapers_registry", False))

    # 2. Database Connectivity
    try:
        from app.database import check_db_connection
        db_ok = await check_db_connection()
        if db_ok:
            print("[*] PostgreSQL: Connected.")
            checks.append(("postgres", True))
        else:
            print("[X] PostgreSQL: FAILED.")
            checks.append(("postgres", False))
    except Exception as e:
        print(f"[X] PostgreSQL check error: {e}")
        checks.append(("postgres", False))

    # 3. Practice Area Bitmask Consistency
    try:
        from app.models.signal import PRACTICE_AREA_BITS
        from app.scrapers.quality_validator import KNOWN_PRACTICE_AREAS
        
        bits_keys = set(PRACTICE_AREA_BITS.keys())
        known_pas = set(KNOWN_PRACTICE_AREAS)
        
        missing_in_bits = known_pas - bits_keys
        missing_in_known = bits_keys - known_pas
        
        if not missing_in_bits and not missing_in_known:
            print("[*] Practice Area Definitions: CONSISTENT.")
            checks.append(("pa_consistency", True))
        else:
            if missing_in_bits:
                print(f"[!] PA Mismatch: KNOWN_PRACTICE_AREAS has {missing_in_bits} not in PRACTICE_AREA_BITS")
            if missing_in_known:
                print(f"[!] PA Mismatch: PRACTICE_AREA_BITS has {missing_in_known} not in KNOWN_PRACTICE_AREAS")
            checks.append(("pa_consistency", False))
    except Exception as e:
        print(f"[X] PA Consistency check error: {e}")
        checks.append(("pa_consistency", False))

    # 4. ML Model Check
    from app.config import get_settings
    settings = get_settings()
    models_dir = settings.models_dir
    expected_models = ["pa_classifier.pkl", "pa_mlb.pkl"]
    missing_models = []
    for m in expected_models:
        if not os.path.exists(os.path.join(models_dir, m)):
            missing_models.append(m)
    
    if not missing_models:
        print(f"[*] ML Models: All {len(expected_models)} present in {models_dir}")
        checks.append(("ml_models", True))
    else:
        print(f"[!] ML Models: MISSING {missing_models} in {models_dir}")
        checks.append(("ml_models", False))

    # Summary
    print("-" * 60)
    failed = [name for name, status in checks if not status]
    if not failed:
        print("[SUCCESS] All pre-launch validation checks passed.")
        return 0
    else:
        print(f"[FAILURE] {len(failed)} checks failed: {failed}")
        return 1

if __name__ == "__main__":
    rc = asyncio.run(validate_all())
    sys.exit(rc)
