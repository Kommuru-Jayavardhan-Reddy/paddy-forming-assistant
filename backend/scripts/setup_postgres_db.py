"""
Paddy Farming Assistant - Database Initialization & Authentication Verification Script
(STEP 11F.2)

Secures interactive database setup:
1. Connects to PostgreSQL 18 via psql.exe using interactive password entry.
2. Checks and creates the dedicated project role 'paddy_app'.
3. Checks and creates the project database 'paddy_farming_db' with owner 'paddy_app'.
4. Interactively verifies connection as 'paddy_app' to 'paddy_farming_db'.
5. Updates backend/.env with the confirmed configuration while preserving all existing settings.
"""

import sys
import os
import getpass
import subprocess
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BACKEND_DIR / ".env"
PSQL_PATH = Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe")

if not PSQL_PATH.exists():
    # Fallback to PATH search if not in default directory
    import shutil
    resolved = shutil.which("psql")
    if resolved:
        PSQL_PATH = Path(resolved)


def run_psql_command(user: str, dbname: str, sql_command: str, password: str, host: str = "127.0.0.1", port: int = 5432) -> subprocess.CompletedProcess:
    """
    Executes a SQL command via psql.exe using PGPASSWORD in a temporary process environment.
    Never prints or logs the password.
    """
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    
    cmd = [
        str(PSQL_PATH),
        "-h", host,
        "-p", str(port),
        "-U", user,
        "-d", dbname,
        "-X",  # do not read .psqlrc
        "-t",  # tuples only
        "-A",  # unaligned output
        "-c", sql_command
    ]
    
    return subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        timeout=15
    )


def test_admin_connection(password: str) -> bool:
    """
    Tests administrative authentication as 'postgres'.
    """
    res = run_psql_command("postgres", "postgres", "SELECT 1;", password)
    return res.returncode == 0 and "1" in res.stdout.strip()


def check_role_exists(admin_password: str, role_name: str = "paddy_app") -> bool:
    """
    Checks if a role exists in pg_roles.
    """
    sql = f"SELECT 1 FROM pg_roles WHERE rolname = '{role_name}';"
    res = run_psql_command("postgres", "postgres", sql, admin_password)
    return res.returncode == 0 and "1" in res.stdout.strip()


def check_db_exists(admin_password: str, db_name: str = "paddy_farming_db") -> bool:
    """
    Checks if a database exists in pg_database.
    """
    sql = f"SELECT 1 FROM pg_database WHERE datname = '{db_name}';"
    res = run_psql_command("postgres", "postgres", sql, admin_password)
    return res.returncode == 0 and "1" in res.stdout.strip()


def create_role(admin_password: str, role_name: str, role_password: str):
    """
    Creates login role with password.
    """
    # Escape single quotes in password if any
    escaped_pw = role_password.replace("'", "''")
    sql = f"CREATE ROLE {role_name} WITH LOGIN PASSWORD '{escaped_pw}';"
    res = run_psql_command("postgres", "postgres", sql, admin_password)
    if res.returncode != 0:
        raise RuntimeError(f"Failed to create role '{role_name}': {res.stderr.strip()}")


def create_database(admin_password: str, db_name: str, owner_role: str):
    """
    Creates project database with owner.
    """
    sql = f"CREATE DATABASE {db_name} OWNER {owner_role};"
    res = run_psql_command("postgres", "postgres", sql, admin_password)
    if res.returncode != 0:
        raise RuntimeError(f"Failed to create database '{db_name}': {res.stderr.strip()}")


def verify_project_user_connection(role_password: str) -> dict:
    """
    Verifies that paddy_app can connect to paddy_farming_db and returns current_database() and current_user.
    """
    sql = "SELECT current_database(), current_user, version();"
    res = run_psql_command("paddy_app", "paddy_farming_db", sql, role_password)
    if res.returncode != 0:
        raise RuntimeError(f"Connection verification failed for paddy_app: {res.stderr.strip()}")
    
    parts = res.stdout.strip().split("|")
    return {
        "database": parts[0] if len(parts) > 0 else "unknown",
        "user": parts[1] if len(parts) > 1 else "unknown",
        "version": parts[2] if len(parts) > 2 else "unknown",
    }


def update_env_password(password: str):
    """
    Updates POSTGRES_PASSWORD in backend/.env while strictly preserving all other variables.
    """
    if not ENV_PATH.exists():
        return
    
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    lines = content.splitlines()
    updated = False
    new_lines = []
    
    for line in lines:
        if line.startswith("POSTGRES_PASSWORD="):
            new_lines.append(f"POSTGRES_PASSWORD={password}")
            updated = True
        else:
            new_lines.append(line)
            
    if not updated:
        new_lines.append(f"POSTGRES_PASSWORD={password}")
        
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")


def main():
    print("=" * 80)
    print("STEP 11F.2 — POSTGRESQL PROJECT DATABASE & USER SETUP")
    print("=" * 80)
    print(f"PostgreSQL Client: {PSQL_PATH}")
    
    if not PSQL_PATH.exists():
        print(f"[ERROR] psql.exe not found at: {PSQL_PATH}")
        sys.exit(1)
        
    print("\n[STEP 1] Administrator Authentication")
    admin_pw = getpass.getpass("Enter PostgreSQL administrator ('postgres') password: ")
    if not admin_pw:
        print("[ERROR] Password cannot be empty.")
        sys.exit(1)
        
    if not test_admin_connection(admin_pw):
        print("\n[FAIL] Administrator authentication failed.")
        print("Please verify the 'postgres' superuser password entered.")
        print("Alternative: You can create the user and database via pgAdmin 4.")
        sys.exit(1)
    print("[PASS] Administrator authentication successful.")
    
    # 2. Check / Create Role 'paddy_app'
    print("\n[STEP 2] Verifying Project User 'paddy_app'")
    role_exists = check_role_exists(admin_pw, "paddy_app")
    if role_exists:
        print("[INFO] Role 'paddy_app' already exists.")
        app_pw = getpass.getpass("Enter password for existing 'paddy_app' role: ")
    else:
        print("[INFO] Role 'paddy_app' does not exist. Creating new role...")
        app_pw = getpass.getpass("Create a password for new 'paddy_app' role: ")
        app_pw_confirm = getpass.getpass("Confirm password for 'paddy_app': ")
        if app_pw != app_pw_confirm:
            print("[ERROR] Passwords do not match.")
            sys.exit(1)
        create_role(admin_pw, "paddy_app", app_pw)
        print("[PASS] Role 'paddy_app' created successfully.")
        
    # 3. Check / Create Database 'paddy_farming_db'
    print("\n[STEP 3] Verifying Project Database 'paddy_farming_db'")
    db_exists = check_db_exists(admin_pw, "paddy_farming_db")
    if db_exists:
        print("[INFO] Database 'paddy_farming_db' already exists.")
    else:
        print("[INFO] Database 'paddy_farming_db' does not exist. Creating...")
        create_database(admin_pw, "paddy_farming_db", "paddy_app")
        print("[PASS] Database 'paddy_farming_db' created successfully with owner 'paddy_app'.")
        
    # 4. Verify Connection as 'paddy_app'
    print("\n[STEP 4] Verifying 'paddy_app' Database Access")
    try:
        conn_info = verify_project_user_connection(app_pw)
        print(f"  Connected Database: {conn_info['database']}")
        print(f"  Current User:       {conn_info['user']}")
        print(f"  PostgreSQL Version: {conn_info['version'][:60]}...")
        assert conn_info["database"] == "paddy_farming_db"
        assert conn_info["user"] == "paddy_app"
        print("[PASS] Database connectivity verified for user 'paddy_app' on 'paddy_farming_db'.")
    except Exception as exc:
        print(f"[FAIL] Verification failed: {exc}")
        sys.exit(1)
        
    # 5. Securely configure backend/.env
    print("\n[STEP 5] Updating backend/.env")
    update_env_password(app_pw)
    print("[PASS] backend/.env updated with POSTGRES_PASSWORD (kept confidential).")
    
    print("\n" + "=" * 80)
    print("STEP 11F.2 DATABASE & USER SETUP COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
