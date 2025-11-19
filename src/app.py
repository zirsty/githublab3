import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import re
import os

DB_NAME = "src/cinema.db"
current_visitor = None


def db_query(query, params=(), fetch=True):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return rows

if not os.path.exists(DB_NAME):
    messagebox.showerror("Ошибка", f"База данных не найдена!\nОжидается файл:\n{DB_NAME}")
    exit()


def validate_phone(phone):
    clean = re.sub(r"[^\d+]", "", phone.strip())
    if re.match(r"^(?:\+7|8)\d{10}$", clean):
        return True, "+7" + clean.lstrip("+78")
    return False, None


def visitor_login(parent):
    global current_visitor
    win = tk.Toplevel(parent)
    win.title("Вход посетителя")
    win.geometry("420x420")
    win.grab_set()

    tk.Label(win, text="Представьтесь", font=("Segoe UI", 16, "bold")).pack(pady=30)

    tk.Label(win, text="Фамилия:").pack(anchor="w", padx=80)
    e_last = tk.Entry(win, width=40, font=("Segoe UI", 11)); e_last.pack(pady=5)

    tk.Label(win, text="Имя:").pack(anchor="w", padx=80)
    e_first = tk.Entry(win, width=40, font=("Segoe UI", 11)); e_first.pack(pady=5)

    tk.Label(win, text="Телефон:").pack(anchor="w", padx=80)
    e_phone = tk.Entry(win, width=40, font=("Segoe UI", 11)); e_phone.pack(pady=5)
    tk.Label(win, text="Пример: +79991234567 или 89991234567", fg="gray", font=9).pack(pady=(0,20))

    def confirm():
        last = e_last.get().strip()
        first = e_first.get().strip()
        phone = e_phone.get().strip()

        if not (last and first and phone):
            messagebox.showerror("Ошибка", "Заполните все поля!")
            return

        valid, norm_phone = validate_phone(phone)
        if not valid:
            messagebox.showerror("Ошибка", "Неверный формат телефона")
            return

        existing = db_query("SELECT id FROM VISITOR WHERE phone = ?", (norm_phone,))
        if existing:
            vid = existing[0][0]
        else:
            vid = db_query("SELECT COALESCE(MAX(id), 0) + 1 FROM VISITOR")[0][0]
            db_query("INSERT INTO VISITOR (id, last_name, first_name, phone) VALUES (?, ?, ?, ?)",
                     (vid, last, first, norm_phone), fetch=False)

        global current_visitor
        current_visitor = {"id": vid, "last_name": last, "first_name": first, "phone": norm_phone}
        win.destroy()
        open_sessions_window(parent)

    tk.Button(win, text="Продолжить", font=("Segoe UI", 12), width=20, command=confirm).pack(pady=10)


def open_sessions_window(parent):
    win = tk.Toplevel(parent)
    win.title("Сеансы в кинотеатре")
    win.geometry("1150x680")

    tree = ttk.Treeview(win, columns=("id","movie","hall","date","time","price","free"), show="headings")
    tree.pack(fill="both", expand=True, padx=15, pady=15)

    headers = ["ID", "Фильм", "Зал", "Дата", "Время", "Цена", "Свободно"]
    widths  = [70,  420,   70,   120,   150,    100,    120]
    for col, text, w in zip(tree["columns"], headers, widths):
        tree.heading(col, text=text)
        tree.column(col, width=w, anchor="center")
    tree.column("movie", anchor="w")

    def refresh():
        for item in tree.get_children():
            tree.delete(item)
        sessions = db_query("""
            SELECT s.id, m.title, h.number, h.capacity, s.session_date, s.start_time, s.end_time, s.price
            FROM SESSION s
            JOIN MOVIE m ON s.movie_id = m.id
            JOIN HALL h ON s.hall_id = h.id
            ORDER BY s.session_date, s.start_time
        """)
        for s in sessions:
            sid, title, hall_num, cap, ts, start, end, price = s
            date_str = datetime.fromtimestamp(ts).strftime("%d.%m.%Y")
            time_str = f"{start//60:02d}:{start%60:02d}–{end//60:02d}:{end%60:02d}"
            taken = len(db_query("SELECT 1 FROM TICKET WHERE session_id = ?", (sid,)))
            free = cap - taken
            tree.insert("", "end", values=(sid, title, hall_num, date_str, time_str, f"{price} ₽", f"{free}/{cap}"))

    tree.bind("<Double-1>", lambda e: open_session_seats(parent, tree.item(tree.focus())["values"][0]))
    refresh()
    tk.Button(win, text="Обновить список", font=12, command=refresh).pack(pady=10)


def open_session_seats(parent, session_id):
    win = tk.Toplevel(parent)
    win.title(f"Выбор мест — сеанс {session_id}")
    win.geometry("1200x800")

    info = db_query("""
        SELECT m.title, h.number, h.capacity, s.price,
            s.session_date,
            s.start_time, s.end_time
        FROM SESSION s
        JOIN MOVIE m ON s.movie_id = m.id
        JOIN HALL h ON s.hall_id = h.id
        WHERE s.id = ?
    """, (session_id,))[0]

    title, hall, capacity, price, session_date_ts, start_min, end_min = info

    date_str = datetime.fromtimestamp(session_date_ts).strftime("%d.%m.%Y")
    time_str = f"{start_min//60:02d}:{start_min%60:02d}–{end_min//60:02d}:{end_min%60:02d}"

    tk.Label(win, text=title, font=("Segoe UI", 18, "bold")).pack(pady=15)
    tk.Label(win, text=f"Зал {hall} • {date_str} • {time_str} • {price} ₽",
         font=("Segoe UI", 11), fg="#333").pack(pady=5)

    taken = {(r,s) for r, s in db_query("SELECT row, seat FROM TICKET WHERE session_id = ?", (session_id,))}
    rows = 12 if capacity >= 120 else 10
    cols = 18 if capacity >= 120 else 15

    frame = tk.Frame(win)
    frame.pack(pady=30)

    tk.Label(frame, text="ЭКРАН", bg="#222", fg="white", font=("Segoe UI", 12), width=80, height=2).grid(row=0, column=0, columnspan=cols+2, pady=(0,30))

    def buy(r, s):
        if (r,s) in taken: return
        if messagebox.askyesno("Подтверждение", f"Купить билет?\nРяд {r}, место {s}\nЦена: {price} ₽"):
            new_id = db_query("SELECT COALESCE(MAX(id),0)+1 FROM TICKET")[0][0]
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db_query("INSERT INTO TICKET VALUES (?,?,?,?,?,?,?)",
                     (new_id, session_id, r, s, current_visitor["id"], now, price), fetch=False)
            messagebox.showinfo("Успех", f"Билет №{new_id} куплен!\nРяд {r}, место {s}")
            win.destroy()
            open_session_seats(parent, session_id)

    for r in range(1, rows+1):
        tk.Label(frame, text=str(r), font=12).grid(row=r+1, column=0, padx=10)
        for s in range(1, cols+1):
            occupied = (r,s) in taken
            btn = tk.Button(frame,
                            text="ЗАНЯТО" if occupied else f"{r}-{s}",
                            width=7, height=2,
                            bg="#ffcccc" if occupied else "#ccffcc",
                            state="disabled" if occupied else "normal",
                            command=lambda r=r,s=s: buy(r,s))
            btn.grid(row=r+1, column=s+1, padx=2, pady=2)

def open_admin_login(root):
    win = tk.Toplevel(root)
    win.title("Администратор")
    win.geometry("340x240")
    win.grab_set()

    tk.Label(win, text="Вход в панель администратора", font=14).pack(pady=20)
    tk.Label(win, text="Логин:").pack()
    e_login = tk.Entry(win, width=30); e_login.pack(pady=5)
    tk.Label(win, text="Пароль:").pack()
    e_pass = tk.Entry(win, show="*", width=30); e_pass.pack(pady=5)

    def login():
        if db_query("SELECT 1 FROM ADMINISTRATOR WHERE login=? AND password=?", (e_login.get(), e_pass.get())):
            win.destroy()
            admin_panel(root)
        else:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")

    tk.Button(win, text="Войти", font=12, width=15, command=login).pack(pady=20)


def admin_panel(root):
    win = tk.Toplevel(root)
    win.title("Админ-панель")
    win.geometry("460x560")
    tk.Label(win, text="АДМИНИСТРАТОР", font=("Segoe UI", 20, "bold")).pack(pady=40)

    buttons = [
        ("Все купленные билеты", lambda: open_tickets_window(win)),
        ("Список фильмов",       lambda: show_movies(win)),
        ("Сеансы",               lambda: open_sessions_window(root)),  # ← root, чтобы не было конфликта
        ("Зарегистрированные посетители", lambda: show_visitors(win)),
        ("Выход",                win.destroy)
    ]

    for text, cmd in buttons:
        tk.Button(win, text=text, font=("Segoe UI", 12), width=32, height=2, command=cmd).pack(pady=12)


def open_tickets_window(parent):
    win = tk.Toplevel(parent)
    win.title("Все билеты")
    win.geometry("1250x700")
    tree = ttk.Treeview(win, columns=("id","fio","phone","movie","date","time","seat","price"), show="headings")
    tree.pack(fill="both", expand=True, padx=10, pady=10)

    for c, h, w in zip(tree["columns"], ["№","ФИО","Телефон","Фильм","Дата","Время","Место","Цена"], [70,200,150,380,110,110,100,100]):
        tree.heading(c, text=h); tree.column(c, width=w, anchor="center")
    tree.column("fio", anchor="w"); tree.column("movie", anchor="w")

    data = db_query("""
        SELECT t.id,
               COALESCE(v.last_name||' '||v.first_name, '—'),
               COALESCE(v.phone, '—'),
               m.title,
               datetime(s.session_date,'unixepoch'),
               time(s.start_time*60,'unixepoch'),
               t.row||'-'||t.seat,
               t.final_price
        FROM TICKET t
        JOIN SESSION s ON t.session_id=s.id
        JOIN MOVIE m ON s.movie_id=m.id
        LEFT JOIN VISITOR v ON t.visitor_id=v.id
        ORDER BY t.id DESC
    """)
    for row in data:
        tree.insert("", "end", values=row)


def show_movies(parent):
    win = tk.Toplevel(parent)
    win.title("Список фильмов")
    win.geometry("1000x550")
    tree = ttk.Treeview(win, columns=("id","title","genre","dur","age","desc"), show="headings")
    tree.pack(fill="both", expand=True, padx=10, pady=10)
    for c, h, w in zip(tree["columns"], ["ID","Название","Жанр","Длит.","Возраст","Описание"], [60,380,100,80,90,400]):
        tree.heading(c, text=h); tree.column(c, width=w)
    for m in db_query("SELECT id,title,genre,duration_min,age_rating,description FROM MOVIE ORDER BY id"):
        tree.insert("", "end", values=m)


def show_visitors(parent):
    win = tk.Toplevel(parent)
    win.title("Посетители")
    win.geometry("700x500")
    tree = ttk.Treeview(win, columns=("id","fio","phone"), show="headings")
    tree.pack(fill="both", expand=True, padx=10, pady=10)
    tree.heading("id", text="ID"); tree.heading("fio", text="ФИО"); tree.heading("phone", text="Телефон")
    tree.column("id", width=80, anchor="center"); tree.column("fio", width=300); tree.column("phone", width=200)
    for v in db_query("SELECT id, last_name||' '||first_name, phone FROM VISITOR ORDER BY id"):
        tree.insert("", "end", values=v)


def main_window():
    root = tk.Tk()
    root.title("КИНОТЕАТР")
    root.geometry("560x500")
    root.configure(bg="#f5f5f5")

    tk.Label(root, text="КИНОТЕАТР", font=("Segoe UI", 34, "bold"), bg="#f5f5f5").pack(pady=80)
    tk.Label(root, text="Добро пожаловать", font=("Segoe UI", 14), bg="#f5f5f5", fg="#444").pack(pady=10)

    tk.Button(root, text="ПОСЕТИТЕЛЬ", font=("Segoe UI", 14), width=34, height=2,
              command=lambda: visitor_login(root)).pack(pady=20)
    tk.Button(root, text="АДМИНИСТРАТОР", font=("Segoe UI", 14), width=34, height=2,
              command=lambda: open_admin_login(root)).pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    main_window()