import sqlite3
import requests
import time
import json
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

def init_db():
    conn = sqlite3.connect("cloud_codeweavers.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS codeweavers_crossties
                 (c4p_id INTEGER PRIMARY KEY, xml_data TEXT, parsed_app_name TEXT)''')
    conn.commit()
    return conn, c

def fetch_crosstie(c4p_id):
    url = f"https://www.codeweavers.com/compatibility/crosstie/{c4p_id}"
    headers = {"User-Agent": "RIFT-Data-Collector/1.0"}
    
    time.sleep(1.0)
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            try:
                root = ET.fromstring(resp.text)
                app_name = root.find(".//app/name")
                name_val = app_name.text if app_name is not None else "Unknown"
                return (c4p_id, resp.text, name_val)
            except ET.ParseError:
                pass
    except Exception:
        pass
    return False

def main():
    conn, c = init_db()
    
    with open("codeweavers_state.json", "r") as f:
        state = json.load(f)
        
    start_id = state["last_id"] + 1
    end_id = start_id + 1000

    print(f"🚀 Scraping CodeWeavers from ID {start_id} to {end_id}...")
    
    count = 0
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_crosstie, i): i for i in range(start_id, end_id)}
        for future in as_completed(futures):
            res = future.result()
            if res:
                c.execute("INSERT OR REPLACE INTO codeweavers_crossties (c4p_id, xml_data, parsed_app_name) VALUES (?, ?, ?)", res)
                count += 1
                if count % 50 == 0:
                    conn.commit()
                    print(f"Saved {count} valid CrossTies...")
                    
    conn.commit()
    conn.close()
    
    # Update state
    state["last_id"] = end_id
    with open("codeweavers_state.json", "w") as f:
        json.dump(state, f)
        
    print(f"✅ Finished! Added {count} new CrossTies to cloud_codeweavers.db")

if __name__ == "__main__":
    main()
