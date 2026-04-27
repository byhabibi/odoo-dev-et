import json
import time
import logging
from datetime import datetime, timezone
from threading import Thread

from core.modbus import PLCClient
from core.gateway import process
from core.buffer import init_db, save
from core.sender import sender_loop

# 🔥 SETUP LOGGING
logging.basicConfig(
    filename='logs/gateway.log',
    level=logging.INFO,
    format='%(asctime)s %(message)s'
)


def read_plc(plc):
    print(f"[START] Thread jalan untuk {plc['code']}")  # debug awal
    logging.info(f"Thread start: {plc['code']}")

    client = PLCClient(plc["ip"], plc["port"])

    while True:
        try:
            value = client.read(plc["register"])

            if value is not None:
                delta = process(plc["code"], value)

                if delta > 0:
                    timestamp = datetime.now(timezone.utc).isoformat()

                    save(plc["code"], "progress", delta, timestamp)

                    msg = f"[DATA] {plc['code']} → {value} (+{delta})"
                    print(msg)
                    logging.info(msg)

        except Exception as e:
            print(f"[ERROR] {plc['code']} → {e}")
            logging.error(f"{plc['code']} error: {e}")

        time.sleep(0.2)


def main():
    print("🚀 STARTING GATEWAY...")
    logging.info("Gateway started")

    init_db()

    with open("config/ip_list_machine.json") as f:
        machines = json.load(f)

    print(f"[INFO] Loaded {len(machines)} machines")

    # 🔥 start PLC threads
    for plc in machines:
        Thread(target=read_plc, args=(plc,), daemon=True).start()

    # 🔥 start sender
    Thread(target=sender_loop, daemon=True).start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()