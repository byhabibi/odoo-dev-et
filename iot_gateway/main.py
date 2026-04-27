import json
import time
from datetime import datetime, timezone
from threading import Thread

from core.modbus import PLCClient
from core.gateway import process
from core.buffer import init_db, save
from core.sender import sender_loop


def read_plc(plc):
    client = PLCClient(plc["ip"], plc["port"])

    while True:
        value = client.read(plc["register"])

        if value is not None:
            delta = process(plc["code"], value)

            if delta > 0:
                timestamp = datetime.now(timezone.utc).isoformat()

                save(plc["code"], "progress", delta, timestamp)

                print(f"[DATA] {plc['code']} → {value} (+{delta})")

        time.sleep(0.2)


def main():
    init_db()

    with open("config/machines.json") as f:
        machines = json.load(f)

    for plc in machines:
        Thread(target=read_plc, args=(plc,), daemon=True).start()

    Thread(target=sender_loop, daemon=True).start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()