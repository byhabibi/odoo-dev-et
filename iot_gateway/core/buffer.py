import sqlite3

DB_NAME = "buffer.db"

# =========================
# Inisialisasi db dulu gess
# =========================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS buffer (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_code TEXT,
        status TEXT,
        counter INTEGER,
        timestamp TEXT,
        sent INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()

# =========================
# Kita simpen dulu di buffer, ntar baru kita push ke Odoo
# =========================
def save(machine_code, status, counter, timestamp):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        INSERT INTO buffer (machine_code, status, counter, timestamp)
        VALUES (?, ?, ?, ?)
    """, (machine_code, status, counter, timestamp))

    conn.commit()
    conn.close()

# =========================
# Tah kita ambil data yang belum dikirm ke Odoo
# =========================
def get_unsent(limit=50):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    rows = c.execute("""
        SELECT id, machine_code, status, counter, timestamp
        FROM buffer
        WHERE sent = 0
        ORDER BY id ASC
        LIMIT ?
    """, (limit,)).fetchall()

    conn.close()
    return rows

# =========================
# Tandain bang yang baju merah jangan sampe loloss
# =========================
def mark_sent(row_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("UPDATE buffer SET sent = 1 WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()