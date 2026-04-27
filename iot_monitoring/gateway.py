import xmlrpc.client
from datetime import datetime, timezone

# ===== KONFIGURASI =====
ODOO_URL = "http://localhost:8069"
DB = "db_odoo"
USERNAME = "admin"
API_KEY = "739a22bf1b86d6f893d45c99c7c0af8ed773c7f3"
MACHINE_CODE = "NF03"
# =======================

# Koneksi XML-RPC
common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USERNAME, API_KEY, {})
print(f"UID: {uid}")

models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

# Fungsi kirim data
def send_data(machine_code, status, counter):
    result = models.execute_kw(
        DB, uid, API_KEY,
        'iot.sensor.data', 'receive_data',
        [machine_code, status, counter,
         datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")]
    )
    return result

# Test kirim data
print(f"\nKirim data ke mesin {MACHINE_CODE}...")
for i in range(1, 51):
    counter = 1
    result = send_data(MACHINE_CODE, "progress", counter)
    print(f"Counter {counter} pcs → {result}")

print("\nDone! Cek Monitoring di Odoo.")