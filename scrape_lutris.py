import sqlite3
import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_lutris_script(slug, name):
    url = f"https://lutris.net/api/games/{slug}"
    headers = {"User-Agent": "RIFT-Data-Collector/1.0"}
    
    time.sleep(1.0)
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return (slug, resp.text)
    except Exception:
        pass
    return 0

def main():
    conn = sqlite3.connect("cloud_lutris.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS lutris_scripts
                 (slug TEXT PRIMARY KEY, json_data TEXT)''')
    conn.commit()

    with open("lutris_pending.json", "r") as f:
        pending_games = json.load(f)
    
    if not pending_games:
        print("✅ No more pending Lutris games!")
        return
        
    batch = pending_games[:1000]
    remaining = pending_games[1000:]
    
    print(f"🚀 Scraping {len(batch)} Lutris scripts... ({len(remaining)} total remaining after this batch)")
    
    count = 0
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_lutris_script, game["slug"], game["name"]): game["slug"] for game in batch}
        for future in as_completed(futures):
            res = future.result()
            if res and res != 0:
                c.execute("INSERT OR REPLACE INTO lutris_scripts (slug, json_data) VALUES (?, ?)", res)
                count += 1
                if count % 50 == 0:
                    conn.commit()
                    print(f"Saved {count} Lutris scripts...")

    conn.commit()
    conn.close()
    
    # Save the remaining games back to state
    with open("lutris_pending.json", "w") as f:
        json.dump(remaining, f)
        
    print(f"✅ Finished! Added {count} new scripts to cloud_lutris.db")

if __name__ == "__main__":
    main()
