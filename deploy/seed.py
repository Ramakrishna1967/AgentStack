from passlib.hash import pbkdf2_sha256
import sqlite3
import os

db_path = "/data/agentstack.db"
api_key = "ak_agentstack_demo_key_2026"
project_id = "demo-simulation"

print(f"Seeding database at {db_path}...")

hashed = pbkdf2_sha256.hash(api_key)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Insert project
cursor.execute("INSERT OR REPLACE INTO projects (id, name, api_key_hash) VALUES (?, ?, ?)", 
               (project_id, 'Demo Simulation', hashed))

# Insert user
cursor.execute("INSERT OR REPLACE INTO users (id, email, hashed_password) VALUES (?, ?, ?)", 
               ('u1', 'demo@agentstack.sh', 'hashed'))

# Link user to project
cursor.execute("INSERT OR REPLACE INTO user_projects (user_id, project_id) VALUES (?, ?)", 
               ('u1', project_id))

conn.commit()
conn.close()
print("Seed successful.")
