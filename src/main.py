# main.py
import os
import sqlite3

DB_PATH = "src/cinema.db"

def create_database():
    os.makedirs("src", exist_ok=True)

    if os.path.exists(DB_PATH):
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
        age INTEGER NOT NULL DEFAULT 18
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

    # ОСТАВЛЯЕМ ТОЛЬКО ЗАЛЫ И АДМИНА
    halls = [(1,1,120),(2,2,80),(3,3,100),(4,4,150),(5,5,60)]
    admins = [(1, "Славик", "andruha", "vlados")]

    cur.executemany("INSERT INTO HALL VALUES (?,?,?)", halls)
    cur.executemany("INSERT INTO ADMINISTRATOR VALUES (?,?,?,?)", admins)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_database()