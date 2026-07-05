import sqlite3
import requests
import time
import json
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def init_db():
    conn = sqlite3.connect("cloud_codeweavers.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS codeweavers_crossties
                 (c4p_id INTEGER PRIMARY KEY, xml_data TEXT, parsed_app_name TEXT)''')
    conn.commit()
    return conn, c

def get_session():
    session = requests.Session()
    retry = Retry(connect=5, read=5, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def fetch_crosstie(session, c4p_id):
    url = f"https://www.codeweavers.com/bin/c4p/{c4p_id}"
    headers = {"User-Agent": "RIFT-Data-Collector/2.0 (Robust Mode)"}
    
    try:
        resp = session.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            try:
                root = ET.fromstring(resp.text)
                
                # Check for explicit API error payloads disguised as 200 OK
                if root.find("error") is not None:
                    return False
                
                # A valid CrossTie MUST have the root tag <c4p> and an <app> tag inside
                if root.tag == "c4p" and root.find("app") is not None:
                    app_name = root.find(".//app/name")
                    name_val = app_name.text if app_name is not None and app_name.text else "Unknown"
                    return (c4p_id, resp.text, name_val)
                
            except ET.ParseError:
                pass
    except Exception as e:
        print(f"Network error on ID {c4p_id}: {e}")
        
    return False

def main():
    conn, c = init_db()
    session = get_session()
    
    with open("codeweavers_state.json", "r") as f:
        state = json.load(f)
        
    start_id = state["last_id"] + 1
    # We scrape in chunks of 1500 to get maximum yield per hour without hitting limits too hard
    end_id = start_id + 1500

    print(f"🚀 Robustly scraping CodeWeavers from ID {start_id} to {end_id}...")
    
    count = 0
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_crosstie, session, i): i for i in range(start_id, end_id)}
        for future in as_completed(futures):
            res = future.result()
            if res:
                c.execute("INSERT OR REPLACE INTO codeweavers_crossties (c4p_id, xml_data, parsed_app_name) VALUES (?, ?, ?)", res)
                count += 1
                if count % 50 == 0:
                    conn.commit()
                    print(f"Saved {count} truly valid CrossTies...")
                    
    conn.commit()
    conn.close()
    
    # Update state unconditionally so it keeps marching forward
    state["last_id"] = end_id
    with open("codeweavers_state.json", "w") as f:
        json.dump(state, f)
        
    print(f"✅ Finished! Added {count} new VALID CrossTies to cloud_codeweavers.db")

if __name__ == "__main__":
    main()
