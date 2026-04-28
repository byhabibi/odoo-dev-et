import xmlrpc.client
from datetime import datetime, timezone
import time

ODOO_URL = "http://localhost:8069"
DB = "db_odoo"
USERNAME = "admin"
API_KEY = "739a22bf1b86d6f893d45c99c7c0af8ed773c7f3"
MACHINE_CODE = "NF 04"
STEP = 100

common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USERNAME, API_KEY, {})
models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

def send_data(counter):
    return models.execute_kw(
        DB, uid, API_KEY,
        'iot.sensor.data', 'receive_data',
        [MACHINE_CODE, "progress", counter,
         datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")]
    )

def reset_counter():
    # Cari machine by name
    machines = models.execute_kw(
        DB, uid, API_KEY,
        'iot.machine', 'search_read',
        [[['name', 'ilike', MACHINE_CODE]]],
        {'fields': ['id', 'name'], 'limit': 1}
    )
    if not machines:
        print(f"Machine {MACHINE_CODE} tidak ditemukan!")
        return False
    
    machine_id = machines[0]['id']
    print(f"Machine ditemukan: {machines[0]['name']} (id={machine_id})")
    
    models.execute_kw(
        DB, uid, API_KEY,
        'iot.machine', 'write',
        [[machine_id], {'counter': 0}]
    )
    return True

# Reset counter dulu
print("Reset counter...")
if not reset_counter():
    exit()
time.sleep(0.5)

# Kirim dengan step besar
print(f"Kirim data ke {MACHINE_CODE} step={STEP}...")
counter = 0
while counter < 10000:
    counter += STEP
    result = send_data(counter)
    print(f"Counter {counter} → {result}")

    if isinstance(result, dict) and result.get('info') == 'WO completed, counter reset':
        print("✅ WO DONE!")
        break

print("Done!")