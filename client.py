import requests, time, os
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.metrics import dp
from PIL import Image as PImage
from kivy.config import Config
from kivy.core.window import Window

SERVER = "https://Quizet.pythonanywhere.com"

Config.set('graphics', 'resizable', False)
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')

Window.size = (360, 640)
Window.clearcolor = (0, 0, 0, 1)

class QuizClient(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not os.path.exists("bg.png"):
            w, h = 900, 1600
            top = (0, 0, 255)
            bottom = (255, 165, 0)
            img = PImage.new("RGB", (w, h))
            for y in range(h):
                r = int(top[0] + (bottom[0] - top[0]) * y / h)
                g = int(top[1] + (bottom[1] - top[1]) * y / h)
                b = int(top[2] + (bottom[2] - top[2]) * y / h)
                for x in range(w):
                    img.putpixel((x, y), (r, g, b))
            img.save("bg.png")
        self.bg = Image(source="bg.png", allow_stretch=True, keep_ratio=False)
        self.add_widget(self.bg)
        self.content = BoxLayout(orientation="vertical", padding=12, spacing=10)
        self.add_widget(self.content)
        self.session_id = None
        self.username = None
        self.phone = None
        self.current_q = None
        self.token = None
        self.expiry = 0
        self.time_event = None
        self.show_login()

    def clear(self):
        self.content.clear_widgets()

    def fixed_input(self, hint):
        t = TextInput(hint_text=hint, multiline=False, size_hint=(1, None), height=dp(40), background_color=(1, 1, 1, 1))
        t.bind(text=self.adjust_input)
        return t

    def adjust_input(self, instance, value):
        max_w = self.width * 2
        instance.width = min(max(len(value) * dp(10), dp(200)), max_w)

    def fixed_button(self, text, fn):
        b = Button(text=text, size_hint=(1, None), height=dp(40), background_color=(0, 1, 1, 1))
        def press_anim(inst):
            inst.background_color = (0.7, 1, 1, 1)
            Clock.schedule_once(lambda dt: fn(inst), 0.05)
        b.bind(on_press=press_anim)
        return b

    def show_login(self):
        self.clear()
        self.content.add_widget(Label(text="Login (username + phone)", font_size=20))
        self.user_in = self.fixed_input("username")
        self.phone_in = self.fixed_input("phone")
        self.content.add_widget(self.user_in)
        self.content.add_widget(self.phone_in)
        self.content.add_widget(self.fixed_button("Login", self.do_login))

    def do_login(self, *a):
        u = self.user_in.text.strip()
        p = self.phone_in.text.strip()
        if not u or not p:
            return
        r = requests.post(SERVER + "/login", json={"username": u, "phone": p})
        if r.status_code == 200:
            self.username = u
            self.phone = p
            self.show_home()
        else:
            self.clear()
            self.content.add_widget(Label(text="Login failed"))

    def show_home(self):
        self.clear()
        self.content.add_widget(Label(text=f"Welcome {self.username}", font_size=18))
        self.content.add_widget(self.fixed_button("Join Quiz", lambda *a: self.show_join()))
        self.content.add_widget(self.fixed_button("Logout", lambda *a: self.logout()))

    def logout(self):
        self.session_id = None
        self.username = None
        self.phone = None
        self.show_login()

    def show_join(self):
        self.clear()
        self.content.add_widget(Label(text="Enter 6-digit quiz code and 12-char access code", font_size=16))
        self.code6 = self.fixed_input("6-digit code")
        self.code12 = self.fixed_input("12-char access code")
        self.content.add_widget(self.code6)
        self.content.add_widget(self.code12)
        self.content.add_widget(self.fixed_button("Join", self.join_quiz))
        self.content.add_widget(self.fixed_button("Back", lambda *a: self.show_home()))
        self.msg = Label(text="")
        self.content.add_widget(self.msg)

    def join_quiz(self, *a):
        six = self.code6.text.strip()
        access = self.code12.text.strip()
        if not six or not access:
            self.msg.text = "Enter both codes"
            return
        payload = {"username": self.username, "phone": self.phone, "quiz_code": six, "access_code": access}
        r = requests.post(SERVER + "/register", json=payload)
        if r.status_code == 200:
            d = r.json()
            self.session_id = d.get("session_id")
            self.show_quiz()
        else:
            try:
                self.msg.text = r.json().get("error", "Join failed")
            except:
                self.msg.text = "Join failed"

    def show_quiz(self):
        self.clear()
        self.q_label = Label(text="Getting question...", font_size=18, halign="center")
        self.content.add_widget(self.q_label)
        self.answer_in = self.fixed_input("Type answer")
        self.content.add_widget(self.answer_in)
        self.submit_btn = self.fixed_button("Submit", self.submit_answer)
        self.content.add_widget(self.submit_btn)
        self.timer_lbl = Label(text="", font_size=16)
        self.content.add_widget(self.timer_lbl)
        self.status_lbl = Label(text="", font_size=14)
        self.content.add_widget(self.status_lbl)
        self.get_question()

    def get_question(self, *a):
        r = requests.post(SERVER + "/get_question", json={"session_id": self.session_id})
        if r.status_code != 200:
            self.status_lbl.text = "Error fetching question"
            return
        d = r.json()
        if d.get("done"):
            self.status_lbl.text = "Quiz finished!"
            Clock.schedule_once(lambda dt: self.show_home(), 1.5)
            return
        q = d.get("question")
        self.current_q = q
        self.token = d.get("token")
        self.expiry = d.get("exp", 0)
        self.q_label.text = q.get("text")
        self.answer_in.text = ""
        self.answer_in.disabled = False
        self.submit_btn.disabled = False
        self.start_countdown(int(self.expiry - time.time()))

    def start_countdown(self, seconds):
        if self.time_event:
            self.time_event.cancel()
        self.time_event = None
        self.time_left = max(0, seconds)
        self.timer_lbl.text = f"Time left: {self.time_left}s"
        def tick(dt):
            self.time_left -= 1
            if self.time_left <= 0:
                if self.time_event:
                    self.time_event.cancel()
                self.timer_lbl.text = "Time's up!"
                self.answer_in.disabled = True
                self.submit_btn.disabled = True
                Clock.schedule_once(lambda dt: self.auto_wrong_submit(), 0.2)
                return False
            self.timer_lbl.text = f"Time left: {self.time_left}s"
            return True
        self.time_event = Clock.schedule_interval(tick, 1)

    def auto_wrong_submit(self):
        if not self.current_q:
            return
        payload = {"session_id": self.session_id, "answer": "WRONG", "token": self.token}
        r = requests.post(SERVER + "/submit_answer", json=payload)
        if r.status_code == 200:
            d = r.json()
            if d.get("done"):
                self.status_lbl.text = "Quiz finished!"
                Clock.schedule_once(lambda dt: self.show_home(), 1.5)
                return
            Clock.schedule_once(lambda dt: self.get_question(), 1)
        else:
            self.status_lbl.text = "Error submitting WRONG"

    def submit_answer(self, *a):
        if not self.current_q:
            return
        ans = self.answer_in.text.strip()
        if not ans:
            self.status_lbl.text = "Type an answer"
            return
        self.answer_in.disabled = True
        self.submit_btn.disabled = True
        if self.time_event:
            self.time_event.cancel()
            self.time_event = None
        payload = {"session_id": self.session_id, "answer": ans, "token": self.token}
        r = requests.post(SERVER + "/submit_answer", json=payload)
        if r.status_code != 200:
            try:
                self.status_lbl.text = r.json().get("error", "Submit failed")
            except:
                self.status_lbl.text = "Submit failed"
            return
        d = r.json()
        if d.get("done"):
            self.status_lbl.text = "Quiz finished!"
            Clock.schedule_once(lambda dt: self.show_home(), 1.5)
            return
        self.status_lbl.text = "Answer recorded"
        Clock.schedule_once(lambda dt: self.get_question(), 1.2)

class QuizApp(App):
    def build(self):
        return QuizClient()

if __name__ == "__main__":
    QuizApp().run()
