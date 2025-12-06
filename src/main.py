import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
import re
import os

DB_NAME = "src/cinema.db"
current_visitor = None

def db_query(query, params=(), fetch=True):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    cur.execute(query, params)
    if fetch:
        result = cur.fetchall()
    else:
        result = None
    conn.commit()
    conn.close()
    return result

def validate_phone(phone):
    clean = re.sub(r"[^\d+]", "", phone.strip())
    if re.match(r"^(?:\+7|8)\d{10}$", clean):
        return True, "+7" + clean.lstrip("+78")[-10:]
    return False, None

def visitor_login(parent):
    global current_visitor
    win = tk.Toplevel(parent)
    win.title("Вход посетителя")
    win.geometry("460x680")
    win.grab_set()

    tk.Label(win, text="Представьтесь", font=("Segoe UI", 16)).pack(pady=30)
    tk.Label(win, text="Фамилия").pack();   e_last  = tk.Entry(win, width=40); e_last.pack(pady=5)
    tk.Label(win, text="Имя").pack();       e_first = tk.Entry(win, width=40); e_first.pack(pady=5)
    tk.Label(win, text="Телефон").pack();   e_phone = tk.Entry(win, width=40); e_phone.pack(pady=5)
    tk.Label(win, text="Возраст").pack();   e_age   = tk.Entry(win, width=40); e_age.pack(pady=8)

    def ok():
        last = e_last.get().strip()
        first = e_first.get().strip()
        phone = e_phone.get().strip()
        age_str = e_age.get().strip()

        def valid_name(s):
            if not s:
                return False
            return bool(re.fullmatch(r"[А-ЯЁA-Z][А-ЯЁA-Zа-яёa-z\s-]*[А-ЯЁA-Zа-яёa-z]", s))

        if not valid_name(last):
            messagebox.showerror("Ошибка", 
                "Некорректная фамилия!\n"
                "Разрешено: только буквы, пробел и дефис\n"
                "Примеры: Иванов, Петров-Сидоров, Ким Чен Ын\n"
                "Запрещено: Александр-, -Иванов, Иван123, Анна!!")
            return

        if not valid_name(first):
            messagebox.showerror("Ошибка", 
                "Некорректное имя!\n"
                "Разрешено: только буквы, пробел и дефис")
            return

        if not all([phone, age_str]):
            messagebox.showerror("Ошибка", "Заполните телефон и возраст!")
            return

        try:
            age = int(age_str)
            if not (1 <= age <= 120):
                raise ValueError
        except:
            messagebox.showerror("Ошибка", "Возраст — число от 1 до 120")
            return

        valid, norm = validate_phone(phone)
        if not valid:
            messagebox.showerror("Ошибка", "Неверный номер телефона\nПример: +79123456789")
            return

        exists = db_query("SELECT id, age FROM VISITOR WHERE phone=?", (norm,))
        if exists:
            vid, db_age = exists[0]
            if db_age != age:
                db_query("UPDATE VISITOR SET age=? WHERE id=?", (age, vid), fetch=False)
        else:
            db_query("INSERT INTO VISITOR (last_name, first_name, phone, age) VALUES (?,?,?,?)",
                     (last, first, norm, age), fetch=False)
            vid = db_query("SELECT last_insert_rowid()")[0][0]

        global current_visitor
        current_visitor = {"id": vid, "name": f"{first} {last}", "age": age}
        win.destroy()
        open_sessions_window(parent)

    tk.Button(win, text="Купить билет", width=25, height=2, bg="#4CAF50", fg="white", command=ok).pack(pady=20)
    tk.Button(win, text="Мои билеты", width=25, height=2, bg="#ff9800", fg="white",
              command=lambda: my_tickets(win)).pack(pady=8)
    tk.Button(win, text="Выйти", width=25, height=2, bg="#f44336", fg="white", command=win.destroy).pack(pady=8)

def open_sessions_window(parent):
    win = tk.Toplevel(parent)
    win.title("Расписание сеансов")
    win.geometry("1350x750")

    tree = ttk.Treeview(win, columns=("id","movie","hall","date","time","price","free","rating"), show="headings")
    tree.pack(fill="both", expand=True, padx=15, pady=15)

    headers = ["ID", "Фильм", "Зал", "Дата", "Время", "Цена", "Свободно", "Рейтинг"]
    widths  = [100, 520, 80, 130, 160, 100, 120, 100]
    for col, text, width in zip(tree["columns"], headers, widths):
        tree.heading(col, text=text)
        tree.column(col, width=width, anchor="center")
    tree.column("movie", anchor="w")

    def refresh():
        for item in tree.get_children():
            tree.delete(item)
        sessions = db_query("""
            SELECT s.id, m.title, h.number, h.capacity, s.session_date,
                   s.start_time, s.end_time, s.price, m.age_rating
            FROM SESSION s
            JOIN MOVIE m ON s.movie_id = m.id
            JOIN HALL h ON s.hall_id = h.id
            ORDER BY s.session_date, s.start_time
        """)
        for sess in sessions:
            sid, title, hall, cap, date, st, end, price, rating = sess
            time_str = f"{st//60:02d}:{st%60:02d}–{end//60:02d}:{end%60:02d}"
            taken = len(db_query("SELECT 1 FROM TICKET WHERE session_id=?", (sid,)))
            free = cap - taken
            tree.insert("", "end", values=(sid, title, hall, date, time_str, f"{price}₽", f"{free}/{cap}", rating))

    def on_double_click(event):
        item_id = tree.focus()
        if not item_id:
            return
        values = tree.item(item_id, "values")
        if values:
            session_id = values[0]
            open_seats(win, session_id)

    tree.bind("<Double-1>", on_double_click)

    tree.bind("<Button-1>", lambda e: "break")
    tree.bind("<Button-1>", lambda e: tree.selection_set(tree.identify_row(e.y)))

    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=12)
    tk.Button(btn_frame, text="Обновить расписание", command=refresh, width=22, bg="#ff9800", fg="white").pack(side="left", padx=15)
    tk.Button(btn_frame, text="Мои билеты", command=lambda: my_tickets(win), width=22, bg="#2196F3", fg="white").pack(side="left", padx=15)
    refresh()
    
    btns = tk.Frame(win)
    btns.pack(pady=10)
    tk.Button(btns, text="Обновить", command=refresh, width=15).pack(side="left", padx=5)
    tk.Button(btns, text="Мои билеты", bg="#ff9800", fg="white", width=20,
              command=lambda: my_tickets(win)).pack(side="left", padx=5)
    
def open_seats(parent, session_id):
    info = db_query("""
        SELECT m.title, h.number, h.capacity, s.price, s.session_date, s.start_time, s.end_time, m.age_rating
        FROM SESSION s JOIN MOVIE m ON s.movie_id=m.id JOIN HALL h ON s.hall_id=h.id WHERE s.id=?
    """, (session_id,))[0]

    title, hall_num, capacity, price, date, st, end, age_rating = info

    rating_num = 0
    if age_rating.endswith("+"):
        try:
            rating_num = int(age_rating[:-1])
        except: pass
    if current_visitor["age"] < rating_num:
        messagebox.showerror("Доступ запрещён", f"Фильм: {age_rating}\nВаш возраст: {current_visitor['age']} лет")
        return

    win = tk.Toplevel(parent)
    win.title(f"{title}")
    win.geometry("1100x780")
    win.minsize(900, 650)
    win.configure(bg="#f5f5f5")
    win.grab_set()

    tk.Label(win, text=title, font=("Segoe UI", 22, "bold"), bg="#f5f5f5").pack(pady=(20, 5))
    tk.Label(win, text=f"Зал {hall_num} • {date} • {st//60:02d}:{st%60:02d}–{end//60:02d}:{end%60:02d} • {price}₽ • {age_rating}",
             font=("Segoe UI", 11), fg="#555", bg="#f5f5f5").pack(pady=(0, 20))

    tk.Label(win, text="ЭКРАН", bg="#222", fg="white", font=("Arial", 14), height=2).pack(fill="x", padx=100, pady=(0, 30))

    if capacity <= 80:
        rows, cols = 8, 10
    elif capacity <= 100:
        rows, cols = 10, 10
    elif capacity <= 120:
        rows, cols = 10, 12
    elif capacity <= 150:
        rows, cols = 10, 15
    else:
        rows, cols = 12, 18

    frame = tk.Frame(win, bg="#f5f5f5")
    frame.pack()

    buttons = {}
    seat_count = 0

    def update_seats():
        taken = {(r, s) for r, s in db_query("SELECT row, seat FROM TICKET WHERE session_id=?", (session_id,))}
        for (r, s), btn in buttons.items():
            if (r, s) in taken:
                btn.config(bg="#ff3b30", text="×", state="disabled")
            else:
                btn.config(bg="#007aff", text=str(s), state="normal")

    def buy(r, s):
        if messagebox.askyesno("Купить билет", f"Место {r} ряд, {s} место — {price}₽"):
            db_query("""
                INSERT INTO TICKET (session_id, row, seat, visitor_id, purchase_datetime, final_price)
                VALUES (?, ?, ?, ?, datetime('now'), ?)
            """, (session_id, r, s, current_visitor["id"], price), fetch=False)
            messagebox.showinfo("Готово", f"Билет на место {r}-{s} куплен!")
            update_seats()

    for r in range(1, rows + 1):
        row_frame = tk.Frame(frame, bg="#f5f5f5")
        row_frame.pack(pady=4)

        tk.Label(row_frame, text=f"{r}", font=("Arial", 11), width=3, bg="#f5f5f5").pack(side="left", padx=(40, 18))

        for s in range(1, cols + 1):
            seat_count += 1
            if seat_count > capacity:
                tk.Label(row_frame, width=4, bg="#f5f5f5").pack(side="left", padx=2)
                continue

            btn = tk.Button(row_frame,
                           text=str(s),
                           width=4, height=1,
                           font=("Arial", 10, "bold"),
                           bg="#007aff", fg="white",
                           relief="flat",
                           bd=0,
                           highlightthickness=2,
                           highlightbackground="#ddd")
            btn.pack(side="left", padx=3, pady=2)
            buttons[(r, s)] = btn
            btn.config(command=lambda rr=r, ss=s: buy(rr, ss))

    update_seats()

    bottom = tk.Frame(win, bg="#f5f5f5")
    bottom.pack(pady=30, fill="x")
    
    tk.Label(bottom, text="Синие — свободно", font=("Arial", 10), fg="#007aff", bg="#f5f5f5").pack(side="left", padx=50)
    tk.Label(bottom, text="Красные × — занято", font=("Arial", 10), fg="#ff3b30", bg="#f5f5f5").pack(side="left", padx=20)
    
    tk.Button(bottom, text="Закрыть", command=win.destroy,
              bg="#888", fg="white", font=("Arial", 11), relief="flat", width=15).pack(side="right", padx=50)
    
def my_tickets(parent):
    if not current_visitor:
        messagebox.showwarning("Ошибка", "Сначала войдите как посетитель")
        return

    win = tk.Toplevel(parent)
    win.title(f"Мои билеты — {current_visitor['name']}")
    win.geometry("1250x700")
    win.grab_set()

    tree = ttk.Treeview(win, columns=("id","movie","hall","date","time","seat","price","cancel"), show="headings")
    tree.pack(fill="both", expand=True, padx=10, pady=10)

    cols = ["№","Фильм","Зал","Дата","Время","Место","Цена","Отменить"]
    widths = [60,420,70,120,140,100,100,120]
    for c, t, w in zip(tree["columns"], cols, widths):
        tree.heading(c, text=t)
        tree.column(c, width=w, anchor="center")
    tree.column("movie", anchor="w")

    def refresh():
        for i in tree.get_children(): tree.delete(i)
        tickets = db_query("""
            SELECT t.id, m.title, h.number, s.session_date, s.start_time, s.end_time, t.row, t.seat, s.price
            FROM TICKET t
            JOIN SESSION s ON t.session_id=s.id
            JOIN MOVIE m ON s.movie_id=m.id
            JOIN HALL h ON s.hall_id=h.id
            WHERE t.visitor_id=?
            ORDER BY s.session_date DESC, s.start_time DESC
        """, (current_visitor["id"],))

        for t in tickets:
            tid, title, hall, date, st, end, row, seat, price = t
            time_str = f"{st//60:02d}:{st%60:02d}–{end//60:02d}:{end%60:02d}"
            seat_str = f"{row}-{seat}"
            iid = f"ticket_{tid}"
            tree.insert("", "end", iid=iid, values=(tid, title, hall, date, time_str, seat_str, f"{price}₽", "ОТМЕНИТЬ"))
            tree.tag_configure(iid, foreground="red", font=("Arial", 10, "underline"))

    def on_click(event):
        region = tree.identify("region", event.x, event.y)
        col = tree.identify_column(event.x)

        if region == "cell" and col == "#8":
            item = tree.identify_row(event.y)
            if item:
                tid = tree.item(item)["values"][0]
                if messagebox.askyesno(
                    "Отмена билета",
                    f"Отменить билет №{tid}?"
                ):
                    db_query("DELETE FROM TICKET WHERE id=?", (tid,), fetch=False)
                    refresh()

    tree.bind("<ButtonRelease-1>", on_click)
    refresh()
    tk.Button(win, text="Обновить список", command=refresh).pack(pady=5)

def admin_login(root):
    win = tk.Toplevel(root)
    win.title("Администратор")
    win.geometry("350x250")
    win.grab_set()
    tk.Label(win, text="Логин").pack(pady=15); e1 = tk.Entry(win, width=30); e1.pack()
    tk.Label(win, text="Пароль").pack(pady=5); e2 = tk.Entry(win, show="*", width=30); e2.pack()
    def check():
        if db_query("SELECT 1 FROM ADMINISTRATOR WHERE login=? AND password=?", (e1.get(), e2.get())):
            win.destroy()
            admin_panel(root)
        else:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")
    tk.Button(win, text="Войти", width=20, height=2, command=check).pack(pady=20)

def admin_panel(root):
    win = tk.Toplevel(root)
    win.title("Админ-панель")
    win.geometry("500x600")
    tk.Label(win, text="АДМИНИСТРАТОР", font=("Segoe UI", 20, "bold")).pack(pady=50)
    tk.Button(win, text="Управление фильмами", width=40, height=2,command=lambda: manage_movies(root)).pack(pady=15)
    tk.Button(win, text="Управление сеансами", width=40, height=2, command=lambda: edit_schedule(root)).pack(pady=15)
    tk.Button(win, text="Все билеты", width=40, height=2, command=lambda: show_all_tickets(win)).pack(pady=10)
    tk.Button(win, text="Посетители", width=40, height=2, command=lambda: show_visitors(win)).pack(pady=10)
    tk.Button(win, text="Выход", width=40, height=2, bg="#f44336", fg="white", command=win.destroy).pack(pady=30)
    
def edit_schedule(root):
    win = tk.Toplevel(root)
    win.title("Управление сеансами")
    win.geometry("1400x800")
    win.grab_set()

    tree = ttk.Treeview(win, columns=("id","movie","hall","date","time","price"), show="headings")
    tree.pack(fill="both", expand=True, padx=15, pady=15)

    headers = ["ID", "Фильм", "Зал", "Дата", "Время", "Цена"]
    widths  = [100, 500, 80, 130, 160, 100]
    for c, h, w in zip(tree["columns"], headers, widths):
        tree.heading(c, text=h)
        tree.column(c, width=w, anchor="center")
    tree.column("movie", anchor="w")

    def refresh():
        for i in tree.get_children(): tree.delete(i)
        sessions = db_query("""
            SELECT s.id, m.title, h.number, s.session_date, 
                   s.start_time, s.end_time, s.price
            FROM SESSION s
            JOIN MOVIE m ON s.movie_id=m.id
            JOIN HALL h ON s.hall_id=h.id
            ORDER BY s.session_date, s.start_time
        """)
        for s in sessions:
            sid, title, hall, date, st, end, price = s
            time_str = f"{st//60:02d}:{st%60:02d}–{end//60:02d}:{end%60:02d}"
            tree.insert("", "end", values=(sid, title, hall, date, time_str, f"{price}₽"))

    def add_session():
        add_win = tk.Toplevel(win)
        add_win.title("Добавить сеанс")
        add_win.geometry("500x550")
        add_win.grab_set()

        movies = db_query("SELECT id, title FROM MOVIE")
        halls  = db_query("SELECT id, number FROM HALL")

        tk.Label(add_win, text="Фильм:", font=12).pack(pady=10)
        movie_combo = ttk.Combobox(add_win, values=[f"{t} (id:{i})" for i,t in movies], state="readonly", width=50)
        movie_combo.pack(pady=5)

        tk.Label(add_win, text="Зал:", font=12).pack(pady=10)
        hall_combo = ttk.Combobox(add_win, values=[f"Зал {n} (вместимость: {db_query('SELECT capacity FROM HALL WHERE id=?', (i,))[0][0]})" 
                                                   for i,n in halls], state="readonly", width=50)
        hall_combo.pack(pady=5)

        tk.Label(add_win, text="Дата (ГГГГ-ММ-ДД):", font=12).pack(pady=10)
        e_date = tk.Entry(add_win, width=30, font=12)
        e_date.insert(0, "2025-12-01")
        e_date.pack(pady=5)

        tk.Label(add_win, text="Время начала (ЧЧ:ММ):", font=12).pack(pady=10)
        e_time = tk.Entry(add_win, width=30, font=12)
        e_time.insert(0, "19:00")
        e_time.pack(pady=5)

        tk.Label(add_win, text="Цена билета:", font=12).pack(pady=10)
        e_price = tk.Entry(add_win, width=30, font=12)
        e_price.insert(0, "800")
        e_price.pack(pady=5)

        def save():
            try:
                movie_idx = movie_combo.current()
                hall_idx  = hall_combo.current()
                if movie_idx < 0 or hall_idx < 0:
                    raise ValueError("Выберите фильм и зал")
                
                movie_id = movies[movie_idx][0]
                hall_id  = halls[hall_idx][0]
                date     = e_date.get().strip()
                time_str = e_time.get().strip()
                price    = int(e_price.get())

                h, m = map(int, time_str.split(":"))
                start_min = h*60 + m

                duration = db_query("SELECT duration_min FROM MOVIE WHERE id=?", (movie_id,))[0][0]
                end_min = start_min + duration

                last_id = db_query("SELECT COUNT(*) FROM SESSION")[0][0]
                new_id = f"sess{last_id + 1}"

                db_query("""
                    INSERT INTO SESSION (id, movie_id, hall_id, session_date, start_time, end_time, price)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (new_id, movie_id, hall_id, date, start_min, end_min, price), fetch=False)

                messagebox.showinfo("Успех", f"Сеанс добавлен!\nID: {new_id}")
                add_win.destroy()
                refresh()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        tk.Button(add_win, text="Добавить сеанс", bg="#4CAF50", fg="white", width=25, height=2, command=save).pack(pady=30)

    def delete_session():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите сеанс для удаления")
            return
        sid = tree.item(selected[0])["values"][0]
        if messagebox.askyesno("Удалить", f"Удалить сеанс {sid}?\nВсе билеты будут отменены!"):
            db_query("DELETE FROM TICKET WHERE session_id=?", (sid,), fetch=False)
            db_query("DELETE FROM SESSION WHERE id=?", (sid,), fetch=False)
            messagebox.showinfo("Готово", "Сеанс удалён")
            refresh()

    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=10)

    tk.Button(btn_frame, text="Добавить сеанс", bg="#2196F3", fg="white", width=20, height=2, command=add_session).pack(side="left", padx=10)
    tk.Button(btn_frame, text="Удалить выбранный", bg="#f44336", fg="white", width=20, height=2, command=delete_session).pack(side="left", padx=10)
    tk.Button(btn_frame, text="Обновить список", bg="#ff9800", fg="white", width=20, height=2, command=refresh).pack(side="left", padx=10)

    refresh()

def manage_movies(root):
    win = tk.Toplevel(root)
    win.title("Управление фильмами")
    win.geometry("1100x700")
    win.grab_set()

    tree = ttk.Treeview(win, columns=("id","title","genre","duration","rating","desc"), show="headings")
    tree.pack(fill="both", expand=True, padx=15, pady=15)

    headers = ["ID", "Название", "Жанр", "Длительность", "Рейтинг", "Описание"]
    widths  = [60, 380, 120, 100, 100, 300]
    for c, h, w in zip(tree["columns"], headers, widths):
        tree.heading(c, text=h)
        tree.column(c, width=w, anchor="center")
    tree.column("title", anchor="w")
    tree.column("desc", anchor="w")

    def refresh():
        for i in tree.get_children():
            tree.delete(i)
        movies = db_query("SELECT id, title, genre, duration_min, age_rating, description FROM MOVIE ORDER BY title")
        for m in movies:
            tree.insert("", "end", values=m)

    def add_movie():
        add_win = tk.Toplevel(win)
        add_win.title("Добавить фильм")
        add_win.geometry("500x600")
        add_win.grab_set()

        tk.Label(add_win, text="Название фильма", font=12).pack(pady=(20,5))
        e_title = tk.Entry(add_win, width=50, font=12); e_title.pack(pady=5)

        tk.Label(add_win, text="Жанр").pack(pady=(15,5))
        e_genre = tk.Entry(add_win, width=50); e_genre.pack(pady=5)

        tk.Label(add_win, text="Длительность (мин)").pack(pady=(15,5))
        e_dur = tk.Entry(add_win, width=20); e_dur.insert(0, "120"); e_dur.pack(pady=5)

        tk.Label(add_win, text="Возрастной рейтинг").pack(pady=(15,5))
        e_rating = ttk.Combobox(add_win, values=["0+", "6+", "12+", "16+", "18+"], state="readonly", width=15)
        e_rating.set("12+")
        e_rating.pack(pady=5)

        tk.Label(add_win, text="Описание").pack(pady=(15,5))
        e_desc = tk.Text(add_win, width=50, height=6)
        e_desc.pack(pady=5)

        def save():
            title = e_title.get().strip()
            genre = e_genre.get().strip()
            desc = e_desc.get("1.0", "end-1c").strip()
            if not title:
                messagebox.showerror("Ошибка", "Введите название фильма!")
                return
            try:
                dur = int(e_dur.get())
                if dur < 30 or dur > 300:
                    raise ValueError
            except:
                messagebox.showerror("Ошибка", "Длительность — число от 30 до 300")
                return

            try:
                db_query("""INSERT INTO MOVIE (title, genre, duration_min, age_rating, description)
                            VALUES (?, ?, ?, ?, ?)""",
                         (title, genre or None, dur, e_rating.get(), desc or None), fetch=False)
                messagebox.showinfo("Готово", f"Фильм «{title}» добавлен!")
                add_win.destroy()
                refresh()
            except sqlite3.IntegrityError:
                messagebox.showerror("Ошибка", "Фильм с таким названием уже существует!")

        tk.Button(add_win, text="Добавить фильм", bg="#4CAF50", fg="white", width=25, height=2, command=save).pack(pady=25)

    def delete_movie():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Внимание", "Выберите фильм для удаления")
            return
        movie_id = tree.item(sel[0])["values"][0]
        title = tree.item(sel[0])["values"][1]
        if messagebox.askyesno("Удалить фильм", f"Удалить фильм «{title}»?\nВсе сеансы с ним тоже удалятся!"):
            db_query("DELETE FROM SESSION WHERE movie_id=?", (movie_id,), fetch=False)
            db_query("DELETE FROM MOVIE WHERE id=?", (movie_id,), fetch=False)
            messagebox.showinfo("Готово", "Фильм и все его сеансы удалены")
            refresh()

    btns = tk.Frame(win)
    btns.pack(pady=10)
    tk.Button(btns, text="Добавить фильм", bg="#2196F3", fg="white", width=20, height=2, command=add_movie).pack(side="left", padx=10)
    tk.Button(btns, text="Удалить выбранный", bg="#f44336", fg="white", width=20, height=2, command=delete_movie).pack(side="left", padx=10)
    tk.Button(btns, text="Обновить", bg="#ff9800", fg="white", width=15, height=2, command=refresh).pack(side="left", padx=10)

    refresh()

def show_all_tickets(parent):
    win = tk.Toplevel(parent)
    win.title("Все билеты")
    win.geometry("1000x600")
    tree = ttk.Treeview(win, columns=("id","session","row","seat","visitor","time"), show="headings")
    tree.pack(fill="both", expand=True, padx=10, pady=10)
    for c, h in zip(tree["columns"], ["№","Сеанс","Ряд","Место","Посетитель","Время"]):
        tree.heading(c, text=h); tree.column(c, anchor="center")
    for row in db_query("SELECT t.id, t.session_id, t.row, t.seat, v.last_name||' '||v.first_name, t.purchase_datetime FROM TICKET t JOIN VISITOR v ON t.visitor_id=v.id"):
        tree.insert("", "end", values=row)

def show_visitors(parent):
    win = tk.Toplevel(parent)
    win.title("Посетители")
    win.geometry("800x600")
    tree = ttk.Treeview(win, columns=("id","fio","phone","age"), show="headings")
    tree.pack(fill="both", expand=True, padx=10, pady=10)
    for c, h, w in zip(tree["columns"], ["ID","ФИО","Телефон","Возраст"], [60,200,150,100]):
        tree.heading(c, text=h); tree.column(c, width=w, anchor="center")
    for row in db_query("SELECT id, last_name||' '||first_name, phone, age FROM VISITOR ORDER BY id DESC"):
        tree.insert("", "end", values=row)

def main_window():
    root = tk.Tk()
    root.title("КИНОТЕАТР")
    root.geometry("600x600")
    root.configure(bg="#1a1a1a")

    tk.Label(root, text="КИНОТЕАТР", font=("Segoe UI", 40, "bold"), fg="#00bcd4", bg="#1a1a1a").pack(pady=120)
    tk.Label(root, text="Система бронирования билетов", font=("Segoe UI", 14), fg="#bbbbbb", bg="#1a1a1a").pack(pady=10)

    tk.Button(root, text="Посетитель", width=35, height=2, bg="#2196F3", fg="white", font=14,
              command=lambda: visitor_login(root)).pack(pady=25)
    tk.Button(root, text="Администратор", width=35, height=2, bg="#e53935", fg="white", font=14,
              command=lambda: admin_login(root)).pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    main_window()