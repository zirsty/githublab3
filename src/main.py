import os
import sqlite3
import json
import csv
import yaml
import xml.etree.ElementTree as ET
from datetime import datetime

def main():
    DB_NAME = "cinema.db"
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.executescript("""
    DROP TABLE IF EXISTS TICKET;
    DROP TABLE IF EXISTS SESSION;
    DROP TABLE IF EXISTS VISITOR;
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
        number INTEGER NOT NULL,
        capacity INTEGER NOT NULL
    );

    CREATE TABLE ADMINISTRATOR (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        login TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    );

    CREATE TABLE SESSION (
        id TEXT PRIMARY KEY,
        movie_id INTEGER NOT NULL,
        hall_id INTEGER NOT NULL,
        session_date INTEGER NOT NULL,
        start_time INTEGER NOT NULL,
        end_time INTEGER NOT NULL,
        price INTEGER NOT NULL,
        FOREIGN KEY(movie_id) REFERENCES MOVIE(id),
        FOREIGN KEY(hall_id) REFERENCES HALL(id)
    );

    CREATE TABLE VISITOR (
        id INTEGER PRIMARY KEY,
        last_name TEXT,
        first_name TEXT,
        phone TEXT
    );

    CREATE TABLE TICKET (
        id INTEGER PRIMARY KEY,
        session_id TEXT NOT NULL,
        row INTEGER NOT NULL,
        seat INTEGER NOT NULL,
        visitor_id INTEGER,
        purchase_datetime TEXT NOT NULL,
        final_price INTEGER NOT NULL
    );
    """)

    movies = [
        (1, "Общество мертвых поэтов", "Комедия,драма", 128, "16+", "фильм про школьников поэтов с крутым учителем, типо Мартына"),
        (2, "Матрица", "Фантастика", 136, "18+", "Там главный герой из фортнайта, норм боевичок на вечер."),
        (3, "Марти великолепный", "Комедия", 149, "16+", "хз не смотрел"),
        (4, "Трансформеры", "фантастика", 143, "16+", "В течение многих столетий две расы роботов-инопланетян — Автоботы и Десептиконы — вели войну, ставкой в которой была судьба Вселенной.")
    ]

    halls = [
        (1, 1, 120),
        (2, 2, 80),
        (3, 3, 100),
        (4, 4, 150),
        (5, 5, 60)
    ]

    admins = [
        (1, "Алеша", "alex228",'qwerty123456'),
        (2, "Славик", "Andruha",'password228')
    ]

    base_date = int(datetime(2025, 11, 16).timestamp())
    sessions = []
    sessions.append(("sess1", 1, 1, base_date, 14*60, 14*60 + 128, 850))
    sessions.append(("sess2", 2, 2, base_date, 18*60, 18*60 + 136, 950))

    visitors = [
        (1, "Ушачини", "Димитрини", "+79992255986"),
        (2, "Соловьев", "Тимофей", "+79999999999"),
        (3, "Ванин", "Роман", "все семерки")
    ]

    purchase_time1 = datetime(2025, 11, 15, 10, 30).isoformat()
    purchase_time2 = datetime(2025, 11, 16, 9, 15).isoformat()

    tickets = [
        (1, "sess1", 5, 12, 1, purchase_time1, 850),
        (2, "sess1", 5, 13, 2, purchase_time1, 850),
        (3, "sess2", 3, 8, 3, purchase_time2, 950),
        (4, "sess2", 3, 9, 1, purchase_time2, 950)
    ]

    cursor.executemany("INSERT INTO MOVIE VALUES (?, ?, ?, ?, ?, ?)", movies)
    cursor.executemany("INSERT INTO HALL VALUES (?, ?, ?)", halls)
    cursor.executemany("INSERT INTO ADMINISTRATOR VALUES (?, ?, ?,?)", admins)
    cursor.executemany("INSERT INTO SESSION VALUES (?, ?, ?, ?, ?, ?, ?)", sessions)
    cursor.executemany("INSERT INTO VISITOR VALUES (?, ?, ?, ?)", visitors)
    cursor.executemany("INSERT INTO TICKET VALUES (?, ?, ?, ?, ?, ?, ?)", tickets)

    conn.commit()

    cursor.execute("""
    SELECT 
        t.id, t.row, t.seat, t.purchase_datetime, t.final_price,
        s.id AS session_id, s.session_date, s.start_time, s.end_time, s.price,
        m.title, m.genre, m.duration_min, m.age_rating, m.description,
        h.number AS hall_number, h.capacity,
        v.last_name, v.first_name, v.phone
    FROM TICKET t
    JOIN SESSION s ON t.session_id = s.id
    JOIN MOVIE m ON s.movie_id = m.id
    JOIN HALL h ON s.hall_id = h.id
    LEFT JOIN VISITOR v ON t.visitor_id = v.id
    ORDER BY t.purchase_datetime, t.id
    """)

    rows = cursor.fetchall()
    data = []

    for row in rows:
        session_date = datetime.fromtimestamp(row[6]).strftime("%Y-%m-%d")
        start_time = f"{row[7]//60:02d}:{row[7]%60:02d}"
        end_time = f"{row[8]//60:02d}:{row[8]%60:02d}"

        ticket_data = {
            "ticket_id": row[0],
            "row": row[1],
            "seat": row[2],
            "purchase_datetime": row[3],
            "final_price": row[4],
            "session": {
                "id": row[5],
                "date": session_date,
                "start_time": start_time,
                "end_time": end_time,
                "price": row[9]
            },
            "movie": {
                "title": row[10],
                "genre": row[11],
                "duration_min": row[12],
                "age_rating": row[13],
                "description": row[14]
            },
            "hall": {
                "number": row[15],
                "capacity": row[16]
            },
            "visitor": {
                "last_name": row[17],
                "first_name": row[18],
                "phone": row[19]
            } if row[17] else None
        }
        data.append(ticket_data)

    os.makedirs("out", exist_ok=True)

    with open("out/cinema.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    with open("out/cinema.csv", "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "ticket_id", "row", "seat", "purchase_datetime", "final_price",
            "session_id", "session_date", "start_time", "end_time", "session_price",
            "movie_title", "genre", "duration_min", "age_rating", "description",
            "hall_number", "hall_capacity",
            "visitor_last_name", "visitor_first_name", "visitor_phone"
        ])
        writer.writeheader()
        for d in data:
            v = d["visitor"] or {}
            writer.writerow({
                "ticket_id": d["ticket_id"],
                "row": d["row"],
                "seat": d["seat"],
                "purchase_datetime": d["purchase_datetime"],
                "final_price": d["final_price"],
                "session_id": d["session"]["id"],
                "session_date": d["session"]["date"],
                "start_time": d["session"]["start_time"],
                "end_time": d["session"]["end_time"],
                "session_price": d["session"]["price"],
                "movie_title": d["movie"]["title"],
                "genre": d["movie"]["genre"],
                "duration_min": d["movie"]["duration_min"],
                "age_rating": d["movie"]["age_rating"],
                "description": d["movie"]["description"],
                "hall_number": d["hall"]["number"],
                "hall_capacity": d["hall"]["capacity"],
                "visitor_last_name": v.get("last_name", ""),
                "visitor_first_name": v.get("first_name", ""),
                "visitor_phone": v.get("phone", "")
            })

    root = ET.Element("cinema_tickets")
    for d in data:
        ticket_elem = ET.SubElement(root, "ticket")
        ET.SubElement(ticket_elem, "id").text = str(d["ticket_id"])
        ET.SubElement(ticket_elem, "row").text = str(d["row"])
        ET.SubElement(ticket_elem, "seat").text = str(d["seat"])
        ET.SubElement(ticket_elem, "purchase_datetime").text = d["purchase_datetime"]
        ET.SubElement(ticket_elem, "final_price").text = str(d["final_price"])

        session_elem = ET.SubElement(ticket_elem, "session")
        for k, v in d["session"].items():
            ET.SubElement(session_elem, k).text = str(v)

        movie_elem = ET.SubElement(ticket_elem, "movie")
        for k, v in d["movie"].items():
            ET.SubElement(movie_elem, k).text = str(v)

        hall_elem = ET.SubElement(ticket_elem, "hall")
        for k, v in d["hall"].items():
            ET.SubElement(hall_elem, k).text = str(v)

        if d["visitor"]:
            visitor_elem = ET.SubElement(ticket_elem, "visitor")
            for k, v in d["visitor"].items():
                ET.SubElement(visitor_elem, k).text = str(v)

    tree = ET.ElementTree(root)
    tree.write("out/cinema.xml", encoding="utf-8", xml_declaration=True)

    with open("out/cinema.yaml", "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    conn.close()

if __name__ == "__main__":
    main()