import xmlrpc.client

ODOO_URL = "http://localhost:8069"
DB = "db_odoo"
USERNAME = "admin"
API_KEY = "isi_api_key_lu"

common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USERNAME, API_KEY, {})

models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")


def send(machine_code, status, counter, timestamp):
    try:
        result = models.execute_kw(
            DB, uid, API_KEY,
            'iot.sensor.data', 'receive_data',
            [machine_code, status, counter, timestamp]
        )
        return result.get("success", False)
    except Exception as e:
        print(f"[SEND ERROR] {e}")
        return False


import time
from core.buffer import get_unsent, mark_sent

def sender_loop():
    while True:
        rows = get_unsent()

        for row in rows:
            row_id, machine_code, status, counter, timestamp = row

            success = send(machine_code, status, counter, timestamp)

            if success:
                mark_sent(row_id)
                print(f"[SENT] {machine_code} +{counter}")
            else:
                print(f"[RETRY] {machine_code}")

        time.sleep(1)