import os
import sqlite3
import json
import csv
import yaml
import xml.etree.ElementTree as ET

DB_PATH = "src/cinema.db"


def create_database():
    os.makedirs("src", exist_ok=True)

    if os.path.exists(DB_PATH):
        export_all_tables()
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    DROP TABLE IF EXISTS TICKET;
    DROP TABLE IF EXISTS VISITOR;
    DROP TABLE IF EXISTS SESSION;
    DROP TABLE IF EXISTS ADMINISTRATOR;
    DROP TABLE IF EXISTS HALL;
    DROP TABLE IF EXISTS MOVIE;

    CREATE TABLE MOVIE (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        genre TEXT,
        duration_min INTEGER,
        age_rating TEXT,
        description TEXT
    );

    CREATE TABLE HALL (
        id INTEGER PRIMARY KEY,
        number INTEGER UNIQUE,
        capacity INTEGER
    );

    CREATE TABLE ADMINISTRATOR (
        id INTEGER PRIMARY KEY,
        name TEXT,
        login TEXT UNIQUE,
        password TEXT
    );

    CREATE TABLE SESSION (
        id TEXT PRIMARY KEY,
        movie_id INTEGER,
        hall_id INTEGER,
        session_date TEXT,
        start_time INTEGER,
        end_time INTEGER,
        price INTEGER
    );

    CREATE TABLE VISITOR (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        last_name TEXT,
        first_name TEXT,
        phone TEXT UNIQUE,
        age INTEGER NOT NULL
    );

    CREATE TABLE TICKET (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        row INTEGER,
        seat INTEGER,
        visitor_id INTEGER,
        purchase_datetime TEXT,
        final_price INTEGER
    );
    """)

    halls = [(1, 1, 120), (2, 2, 80), (3, 3, 100), (4, 4, 150), (5, 5, 60)]
    admins = [(1, "Славик", "andruha", "vlados")]

    cur.executemany("INSERT INTO HALL VALUES (?,?,?)", halls)
    cur.executemany("INSERT INTO ADMINISTRATOR VALUES (?,?,?,?)", admins)

    conn.commit()
    conn.close()

    export_all_tables()


def fetch_tables():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t["name"] for t in cur.fetchall()]

    data = {}
    for table in tables:
        cur.execute(f"SELECT * FROM {table}")
        rows = cur.fetchall()
        data[table] = [dict(row) for row in rows]

    conn.close()
    return data

OUT_DIR = "out"


def export_json(data):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(f"{OUT_DIR}/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def export_csv(data):
    os.makedirs(f"{OUT_DIR}/csv", exist_ok=True)

    for table, rows in data.items():
        if not rows:
            continue

        with open(f"{OUT_DIR}/csv/{table}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)


def export_yaml(data):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(f"{OUT_DIR}/data.yaml", "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)


def export_xml(data):
    os.makedirs(OUT_DIR, exist_ok=True)

    root = ET.Element("database")

    for table, rows in data.items():
        table_el = ET.SubElement(root, table)
        for row in rows:
            row_el = ET.SubElement(table_el, "row")
            for key, value in row.items():
                col = ET.SubElement(row_el, key)
                col.text = str(value)

    tree = ET.ElementTree(root)
    tree.write(f"{OUT_DIR}/data.xml", encoding="utf-8", xml_declaration=True)


def export_all_tables():
    data = fetch_tables()
    export_json(data)
    export_csv(data)
    export_yaml(data)
    export_xml(data)
    print("Файлы JSON, CSV, YAML, XML сохранены в папку out/")


if __name__ == "__main__":
    create_database()
