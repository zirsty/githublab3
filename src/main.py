import os
import sqlite3
import json
import csv
import yaml
import xml.etree.ElementTree as ET
from datetime import datetime

def main():
    os.makedirs("src", exist_ok=True)
    os.makedirs("out", exist_ok=True)

    DB_PATH = "src/cinema.db"

    if os.path.exists(DB_PATH):
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
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
        session_date INTEGER,
        start_time INTEGER,
        end_time INTEGER,
        price INTEGER,
        FOREIGN KEY(movie_id) REFERENCES MOVIE(id),
        FOREIGN KEY(hall_id) REFERENCES HALL(id)
    );

    CREATE TABLE VISITOR (
        id INTEGER PRIMARY KEY,
        last_name TEXT,
        first_name TEXT,
        phone TEXT UNIQUE
    );

    CREATE TABLE TICKET (
        id INTEGER PRIMARY KEY,
        session_id TEXT,
        row INTEGER,
        seat INTEGER,
        visitor_id INTEGER,
        purchase_datetime TEXT,
        final_price INTEGER
    );
    """)

    movies = [
        (1, "Общество мертвых поэтов", "Драма", 128, "16+", "Учитель вдохновляет учеников жить по-настоящему"),
        (2, "Матрица", "Фантастика",136, "18+", "Хакер узнаёт, что мир — симуляция"),
        (3, "Крестный отец", "Комедия", 149, "16+", "крутяк"),
        (4, "Трансформеры", "Боевик", 143, "12+", "Война автоботов и десептиконов на Земле"),
        (5, "Начало", "Триллер", 148, "16+", "Вор проникает в чужие сны, чтобы украсть или внедрить идею")
    ]

    halls = [(1,1,120), (2,2,80), (3,3,100), (4,4,150), (5,5,60)]

    admins = [
        (1, "Алексей", "alex228", "qwerty123456"),
        (2, "Владислав", "Andruha", "password228")
    ]

    date_ts = "20.11.2025"

    sessions = [
        ("sess1", 1, 1, date_ts, 14*60, 14*60 + 128, 850),
        ("sess2", 2, 2, date_ts, 18*60, 18*60 + 136, 950),
        ("sess3", 3, 3, date_ts, 15*60, 15*60 + 149, 900),
        ("sess4", 4, 4, date_ts, 20*60, 20*60 + 143, 1100),
        ("sess5", 5, 5, date_ts, 19*60, 19*60 + 148, 1200)
    ]

    cursor.executemany("INSERT INTO MOVIE VALUES (?,?,?,?,?,?)", movies)
    cursor.executemany("INSERT INTO HALL VALUES (?,?,?)", halls)
    cursor.executemany("INSERT INTO ADMINISTRATOR VALUES (?,?,?,?)", admins)
    cursor.executemany("INSERT INTO SESSION VALUES (?,?,?,?,?,?,?)", sessions)
    conn.commit()

    cursor.execute("""
    SELECT s.id, m.title, m.genre, m.duration_min, m.age_rating, m.description,
           h.number, h.capacity, s.session_date, s.start_time, s.end_time, s.price
    FROM SESSION s
    JOIN MOVIE m ON s.movie_id = m.id
    JOIN HALL h ON s.hall_id = h.id
    """)

    data = []
    for row in cursor.fetchall():
        sid, title, genre, dur, age, desc, hall, cap, ts, st, end, price = row
        data.append({
            "session_id": sid,
            "movie": {
                "title": title,
                "genre": genre,
                "duration_min": dur,
                "age_rating": age,
                "description": desc
            },
            "hall": hall,
            "capacity": cap,
            "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d"),
            "time": f"{st//60:02d}:{st%60:02d}–{end//60:02d}:{end%60:02d}",
            "price": price,
            "free_seats": cap
        })

    with open("out/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    with open("out/data.yaml", "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    with open("out/data.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["session_id","title","genre","duration","age","description","hall","capacity","date","time","price","free_seats"])
        for d in data:
            m = d["movie"]
            writer.writerow([d["session_id"], m["title"], m["genre"], m["duration_min"], m["age_rating"], m["description"],
                             d["hall"], d["capacity"], d["date"], d["time"], d["price"], d["free_seats"]])

    root = ET.Element("sessions")
    for d in data:
        sess = ET.SubElement(root, "session")
        ET.SubElement(sess, "id").text = d["session_id"]
        movie = ET.SubElement(sess, "movie")
        for k, v in d["movie"].items():
            ET.SubElement(movie, k).text = str(v)
        for k in ["hall","capacity","date","time","price","free_seats"]:
            ET.SubElement(sess, k).text = str(d[k])
    ET.ElementTree(root).write("out/data.xml", encoding="utf-8", xml_declaration=True)

    conn.close()

if __name__ == "__main__":
    main()