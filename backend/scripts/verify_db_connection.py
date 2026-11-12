"""
Paddy Farming Assistant - Database Connection Verification
(STEP 11F.2 Non-Destructive Verification)
Reads database settings from backend/.env and validates connectivity
without exposing credentials.
"""

import sys
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BACKEND_DIR / ".env"
PSQL_PATH = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")

if not PSQL_PATH.exists():
    import shutil
    resolved = shutil.which("psql")
    if resolved:
        PSQL_PATH = Path(resolved)


def verify_connection() -> dict:
    if not ENV_PATH.exists():
        return {"status": "FAIL", "reason": "backend/.env not found"}
        
    load_dotenv(dotenv_path=ENV_PATH)
    
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "paddy_farming_db")
    user = os.getenv("POSTGRES_USER", "paddy_app")
    password = os.getenv("POSTGRES_PASSWORD", "")
    
    if not password:
        return {
            "status": "ACTION REQUIRED",
            "reason": "POSTGRES_PASSWORD is empty in backend/.env",
            "host": host,
            "port": port,
            "dbname": dbname,
            "user": user,
        }
        
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    
    cmd = [
        str(PSQL_PATH),
        "-h", host,
        "-p", str(port),
        "-U", user,
        "-d", dbname,
        "-X",
        "-t",
        "-A",
        "-c", "SELECT current_database(), current_user, inet_server_addr();"
    ]
    
    try:
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=10)
        if res.returncode != 0:
            return {
                "status": "FAIL",
                "reason": res.stderr.strip(),
                "host": host,
                "port": port,
                "dbname": dbname,
                "user": user,
            }
            
        parts = res.stdout.strip().split("|")
        return {
            "status": "PASS",
            "database": parts[0] if len(parts) > 0 else "unknown",
            "user": parts[1] if len(parts) > 1 else "unknown",
            "server_addr": parts[2] if len(parts) > 2 else "unknown",
            "host": host,
            "port": port,
        }
    except Exception as exc:
        return {"status": "FAIL", "reason": str(exc)}


if __name__ == "__main__":
    result = verify_connection()
    print("=" * 80)
    print("DATABASE CONNECTION VERIFICATION")
    print("=" * 80)
    print(f"Status: {result['status']}")
    for k, v in result.items():
        if k != "status":
            print(f"  {k}: {v}")
    print("=" * 80)
    sys.exit(0 if result["status"] == "PASS" else 1)
