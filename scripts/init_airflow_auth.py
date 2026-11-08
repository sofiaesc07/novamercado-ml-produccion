"""Initialize a persistent password file for Airflow 3 simple auth manager."""
import json
import os
from pathlib import Path

path = Path(os.environ["AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_PASSWORDS_FILE"])
path.parent.mkdir(parents=True, exist_ok=True)
if path.exists():
    contents = json.loads(path.read_text(encoding="utf-8"))
    if "admin" not in contents:
        raise RuntimeError("Existing Airflow password file has no admin user")
    print("Airflow password file already exists; keeping credentials")
else:
    password = os.environ["AIRFLOW_PASSWORD"]
    if not password:
        raise RuntimeError("AIRFLOW_PASSWORD cannot be blank")
    path.write_text(json.dumps({"admin": password}) + "\n", encoding="utf-8")
    path.chmod(0o600)
    print("Airflow password file initialized")
