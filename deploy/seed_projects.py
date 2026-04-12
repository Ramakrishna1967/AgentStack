import sqlite3
import os

db_path = "/data/agentstack.db"
if not os.path.exists(db_path):
    print(f"Error: DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Ensure projects table exists and has correct columns
conn.execute("""
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    api_key_hash TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# Insert the missing projects
projects = [
    ("demo-simulation", "Demo Simulation", "ak_agentstack_demo_key_2026"),
    ("real-world-test", "Real World Test", "ak_agentstack_demo_key_2026")
]

for p_id, p_name, p_key in projects:
    conn.execute(
        "INSERT OR IGNORE INTO projects (id, name, api_key_hash) VALUES (?, ?, ?)",
        (p_id, p_name, p_key)
    )
    print(f"Ensured project: {p_id}")

conn.commit()
conn.close()
print("Database seeding complete.")
