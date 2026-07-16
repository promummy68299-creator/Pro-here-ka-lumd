import sqlite3

DB_NAME = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price TEXT,
            validity TEXT,
            delivery_link TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plan_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER,
            file_id TEXT,
            media_type TEXT,
            FOREIGN KEY(plan_id) REFERENCES plans(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('welcome_text', 'Welcome to our Premium Service! 🚀')")
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def set_setting(key, value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def add_plan(name, price, validity):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO plans (name, price, validity) VALUES (?, ?, ?)", (name, price, validity))
    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return plan_id

def get_plans():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, validity, delivery_link FROM plans")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_plan(plan_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, validity, delivery_link FROM plans WHERE id = ?", (plan_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def delete_plan(plan_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
    cursor.execute("DELETE FROM plan_media WHERE plan_id = ?", (plan_id,))
    conn.commit()
    conn.close()

def update_plan_link(plan_id, link):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE plans SET delivery_link = ? WHERE id = ?", (link, plan_id))
    conn.commit()
    conn.close()

def add_plan_media(plan_id, file_id, media_type):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO plan_media (plan_id, file_id, media_type) VALUES (?, ?, ?)", (plan_id, file_id, media_type))
    conn.commit()
    conn.close()

def get_plan_media(plan_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, media_type FROM plan_media WHERE plan_id = ?", (plan_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows
