import sqlite3
import json

# Extract CodeWeavers max ID
cw_conn = sqlite3.connect("/Users/abhinawsingh/RIFT/data/codeweavers/codeweavers.db")
cw_c = cw_conn.cursor()
cw_c.execute("SELECT max(c4p_id) FROM codeweavers_crossties")
max_id = cw_c.fetchone()[0] or 0
with open("/Users/abhinawsingh/RIFT/data_repo_clone/codeweavers_state.json", "w") as f:
    json.dump({"last_id": max_id}, f)

# Extract Lutris pending games
lut_conn = sqlite3.connect("/Users/abhinawsingh/RIFT/data/lutris/lutris.db")
lut_c = lut_conn.cursor()
lut_c.execute("SELECT slug, name FROM lutris_games")
games = lut_c.fetchall()
lut_c.execute("SELECT game_slug FROM lutris_scripts")
downloaded = set(row[0] for row in lut_c.fetchall())
pending = [{"slug": s, "name": n} for s, n in games if s not in downloaded]

with open("/Users/abhinawsingh/RIFT/data_repo_clone/lutris_pending.json", "w") as f:
    json.dump(pending, f)

print(f"Extracted CW start ID: {max_id}")
print(f"Extracted {len(pending)} pending Lutris games.")
