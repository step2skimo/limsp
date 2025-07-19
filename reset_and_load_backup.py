import os
import json
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
db_path = BASE_DIR / "db.sqlite3"
backup_file = None

# 1. Locate db.backup.json file
for file in BASE_DIR.glob("**/*"):
    if file.name.lower() in ["db.backup.json", "db_backup.json"]:
        backup_file = file
        break

if not backup_file:
    print("❌ Could not find db.backup.json or db_backup.json in the project folder.")
    exit(1)

print(f"Found backup file: {backup_file}")

# 2. Validate JSON
try:
    with open(backup_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("JSON fixture must be a list of objects.")
except Exception as e:
    print(f"❌ Invalid JSON file: {e}")
    exit(1)

# 3. Delete db.sqlite3
if db_path.exists():
    print(f"Deleting old database: {db_path}")
    os.remove(db_path)
else:
    print("No existing db.sqlite3 found.")

# 4. Run migrations
print("Running migrations...")
subprocess.run(["python", "manage.py", "migrate"], check=True)

# 5. Load the backup fixture
print(f"Loading backup data from {backup_file}...")
subprocess.run(["python", "manage.py", "loaddata", str(backup_file)], check=True)

print("✅ Database reset and data loaded successfully!")
