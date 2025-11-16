import flet as ft
import requests
import time
import threading
import os

SERVER = "https://Quizet.pythonanywhere.com"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(BASE_DIR, "assets", "DancingScript-Regular.ttf")
c = ""

def main(page: ft.Page):
    page.title = "Quizet"
    page.window.full_screen = True
    page.window.maximized = True
    page.window.resizable = False
    page.padding = 0
    page.margin = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.Colors.BLACK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.fonts = {"Dancing": FONT_FILE}
    page.theme = ft.Theme(font_family="Dancing")

    state = {"session_id": None, "username": None, "phone": None, "token": None, "expiry": 0}
    stop_timer = threading.Event()

    bg = ft.Image(src=os.path.join(BASE_DIR, "assets", "bg.png"), fit=ft.ImageFit.COVER)
    overlay = ft.Stack([bg], expand=True)
    page.add(overlay)

    def resize_bg(e):
        bg.width = page.window.width or page.width
        bg.height = page.window.height or page.height
        page.update()

    page.on_resize = resize_bg
    resize_bg(None)

    logo = ft.Image(src=os.path.join(BASE_DIR, "assets", "logo.png"), width=60, height=60, opacity=0.4)
    title = ft.Text("QUIZET", size=32, weight=ft.FontWeight.BOLD, color="white")
    content = ft.Column(spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    overlay.controls.append(
        ft.Container(
            expand=True,
            alignment=ft.alignment.center,
            content=ft.Column(
                [title, logo, content],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )
    )

    def toggle_font(e):
        if e.control.value:
            page.theme = ft.Theme(font_family="Times New Roman")
        else:
            page.theme = ft.Theme(font_family="Dancing")
        page.update()

    font_switch = ft.Switch(label="Font", value=False, on_change=toggle_font)
    overlay.controls.append(
        ft.Container(
            content=font_switch,
            alignment=ft.alignment.bottom_right,
            right=20,
            bottom=20
        )
    )

    def clear():
        content.controls.clear()
        page.update()

    def show_login():
        clear()
        user_in = ft.TextField(label="Username", width=260)
        phone_in = ft.TextField(label="Phone", width=260)
        msg = ft.Text("", size=18, color="white")

        def do_login(e):
            u = (user_in.value or "").strip()
            p = (phone_in.value or "").strip()
            if not u or not p:
                msg.value = "Enter username and phone"
                page.update()
                return
            try:
                r = requests.post(SERVER + "/login", json={"username": u, "phone": p}, timeout=10)
                if r.status_code == 200:
                    state["username"] = u
                    state["phone"] = p
                    show_home()
                    return
            except Exception:
                pass
            msg.value = "Login failed"
            page.update()

        btn = ft.ElevatedButton("Login", on_click=do_login, width=200)
        content.controls.extend([
            ft.Text("Login (username + phone)", size=22),
            user_in,
            phone_in,
            btn,
            msg
        ])
        page.update()

    def show_home():
        clear()
        content.controls.append(ft.Text(f"Welcome {state.get('username')}", size=24))
        content.controls.append(ft.ElevatedButton("Join Quiz", on_click=lambda e: show_join(), width=200))
        content.controls.append(ft.ElevatedButton("Logout", on_click=lambda e: logout(), width=200))
        page.update()

    def logout():
        state.update({"session_id": None, "username": None, "phone": None, "token": None, "expiry": 0})
        show_login()

    def show_join():
        clear()
        code6 = ft.TextField(label="6-digit code", width=260)
        code12 = ft.TextField(label="12-char access code", width=260)
        msg = ft.Text("", size=18, color="white")

        def join_quiz(e):
            global c
            six = (code6.value or "").strip()
            access = (code12.value or "").strip()
            if not six or not access:
                msg.value = "Enter both codes"
                page.update()
                return
            payload = {
                "username": state.get("username"),
                "phone": state.get("phone"),
                "quiz_code": six,
                "access_code": access
            }
            try:
                r = requests.post(SERVER + "/register", json=payload, timeout=10)
                if r.status_code == 200:
                    d = r.json()
                    state["session_id"] = d.get("session_id")
                    c = six
                    show_quiz()
                    return
                else:
                    try:
                        msg.value = r.json().get("error", "Join failed")
                    except Exception:
                        msg.value = "Join failed"
            except Exception:
                msg.value = "Error connecting to server"
            page.update()

        content.controls.extend([
            ft.Text("Enter 6-digit quiz code and 12-char code", size=20),
            code6,
            code12,
            ft.ElevatedButton("Join", on_click=join_quiz, width=200),
            ft.ElevatedButton("Back", on_click=lambda e: show_home(), width=200),
            msg
        ])
        page.update()

    def show_quiz():
        clear()
        q_label = ft.Text("Getting question...", size=22, text_align=ft.TextAlign.CENTER)
        answer_in = ft.TextField(label="Type answer", width=260)
        submit_btn = ft.ElevatedButton("Submit", width=200)
        timer_lbl = ft.Text("", size=18)
        status_lbl = ft.Text("", size=18)

        content.controls.extend([q_label, answer_in, submit_btn, timer_lbl, status_lbl])
        page.update()

        def get_question():
            try:
                r = requests.post(SERVER + "/get_question", json={"session_id": state.get("session_id")}, timeout=10)
                if r.status_code != 200:
                    status_lbl.value = "Error fetching question"
                    page.update()
                    return
                d = r.json()
                if d.get("done"):
                    status_lbl.value = "Quiz finished!"
                    page.update()
                    time.sleep(1.5)
                    show_home()
                    return
                q = d.get("question") or {}
                state["token"] = d.get("token")
                state["expiry"] = d.get("exp", 0)
                q_label.value = q.get("text", "No text")
                answer_in.value = ""
                answer_in.disabled = False
                submit_btn.disabled = False
                start_countdown(int(state.get("expiry", 0) - time.time()))
                page.update()
            except Exception:
                status_lbl.value = "Error fetching question"
                page.update()

        def auto_wrong_submit():
            payload = {"session_id": state.get("session_id"), "answer": "WRONG", "token": state.get("token")}
            try:
                r = requests.post(SERVER + "/submit_answer", json=payload, timeout=10)
                if r.status_code == 200:
                    d = r.json()
                    if d.get("done"):
                        status_lbl.value = "Quiz finished!"
                        page.update()
                        time.sleep(1.5)
                        show_home()
                        return
                time.sleep(0.8)
                get_question()
                return
            except Exception:
                pass
            status_lbl.value = "Error submitting WRONG"
            page.update()

        def start_countdown(seconds):
            stop_timer.clear()
            def tick():
                nonlocal seconds
                while seconds > 0 and not stop_timer.is_set():
                    timer_lbl.value = f"Time left: {seconds}s"
                    page.update()
                    time.sleep(1)
                    seconds -= 1
                if not stop_timer.is_set() and seconds <= 0:
                    timer_lbl.value = "Time's up!"
                    answer_in.disabled = True
                    submit_btn.disabled = True
                    page.update()
                    auto_wrong_submit()
            threading.Thread(target=tick, daemon=True).start()

        def submit_answer(e):
            ans = (answer_in.value or "").strip()
            if not ans:
                status_lbl.value = "Type an answer"
                page.update()
                return
            answer_in.disabled = True
            submit_btn.disabled = True
            stop_timer.set()
            payload = {"session_id": state.get("session_id"), "answer": ans, "token": state.get("token")}
            try:
                r = requests.post(SERVER + "/submit_answer", json=payload, timeout=10)
                if r.status_code != 200:
                    try:
                        status_lbl.value = r.json().get("error", "Submit failed")
                    except Exception:
                        status_lbl.value = "Submit failed"
                    page.update()
                    return
                d = r.json()
                if d.get("done"):
                    status_lbl.value = "Quiz finished!"
                    page.update()
                    time.sleep(1.5)
                    show_home()
                    return
                status_lbl.value = "Answer recorded"
                page.update()
                time.sleep(1.2)
                get_question()
                return
            except Exception:
                status_lbl.value = "Error submitting answer"
                page.update()

        def handle(e):
            if e.data == "resume":
                try:
                    requests.post(SERVER + "/ping", json={"username": state.get("username"), "code": c}, timeout=5)
                except:
                    print("Fail")

        submit_btn.on_click = submit_answer
        page.on_app_lifecycle_state_change = handle

        get_question()

    
    def bgh():
        while True:
            resize_bg(2)
            page.update()
            time.sleep(1)
        


    threading.Thread(target=bgh, daemon=True).start()
    show_login()
    

ft.app(target=main)
