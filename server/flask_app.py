import os, time, json, secrets, string, threading, hmac, hashlib
from tempfile import NamedTemporaryFile
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session, send_file

APP_ROOT = "/home/Quizet/mysite"
QUESTIONS_FILE = os.path.join(APP_ROOT, "questions.txt")
CODES_PATH = os.path.join(APP_ROOT, "codes.json")
USERS_PATH = os.path.join(APP_ROOT, "users.json")
RESULTS_PATH = os.path.join(APP_ROOT, "results.json")
ADMIN_PASSWORD = "admin123"
SECRET = b"supersecret"
QUESTION_EXPIRY = 15
ALPHANUM = string.ascii_letters + string.digits

app = Flask(__name__)
app.secret_key = "quizet_admin_secret"

active_quizzes = {}
sessions = {}
results_data = {}
codes = {}
users = {}

def clear_file_contents(file_path):
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            return

    try:
        with open(file_path, 'w') as f:
            pass
    except IOError:
        pass

def load_json(p):
    if os.path.exists(p):
        with open(p, "r", encoding="utf8") as f:
            return json.load(f)
    return {}

def save_json(p, d):
    with open(p, "w", encoding="utf8") as f:
        json.dump(d, f, indent=2)

def load_quizzes():
    quizzes = {}
    if not os.path.exists(QUESTIONS_FILE):
        return quizzes
    with open(QUESTIONS_FILE, encoding="utf8") as qf:
        lines = [l.rstrip("\n") for l in qf]
    quiz_name = None
    qlist = []
    for l in lines:
        if l.startswith("^"):
            if quiz_name and qlist:
                quizzes[quiz_name] = qlist
            quiz_name = l[1:].strip()
            qlist = []
            continue
        if l.strip():
            qlist.append({"id": secrets.token_hex(8), "text": l.strip()})
    if quiz_name and qlist:
        quizzes[quiz_name] = qlist
    return quizzes

QUIZZES = load_quizzes()
codes = load_json(CODES_PATH)
users = load_json(USERS_PATH)
results_data = load_json(RESULTS_PATH)

def gen_12():
    return ''.join(secrets.choice(ALPHANUM) for _ in range(12))

def sign_payload(payload):
    return hmac.new(SECRET, json.dumps(payload, sort_keys=True).encode(), hashlib.sha256).hexdigest()

def verify_payload(payload, sig):
    return hmac.compare_digest(sign_payload(payload), sig)

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_panel"))
        return render_template_string("""<style>
        body { background-color: black; }
        .glowing { text-shadow: 0 0 20px cyan, 0 0 25px cyan, 0 0 30px cyan; color: cyan; }
        .green { color: rgb(57, 255, 20); text-shadow: 0 0 10px rgba(0, 255, 0, 0.8), 0 0 30px rgba(0, 255, 0, 0.4); }
        .red { color: rgb(247, 33, 25); text-shadow: 0 0 10px rgba(255, 0, 0, 1), 0 0 30px rgba(255, 0, 0, 1); }
        .blue{ color: rgb(57, 20, 255); text-shadow: 0 0 10px rgba(0, 0, 255, 0.8), 0 0 30px rgba(0, 0, 255, 0.4); }
        .purple {color: rgb(128, 0, 128);text-shadow: 0 0 10px rgba(128, 0, 128, 0.8), 0 0 30px rgba(128, 0, 128, 0.4);
        }
    </style>
    <h3 class="red">Wrong password</h3><a href='/admin'>Try again</a>""")
    return render_template_string('''
    <style>
        body { background-color: black; }
        .glowing { text-shadow: 0 0 20px cyan, 0 0 25px cyan, 0 0 30px cyan; color: cyan; }
        .green { color: rgb(57, 255, 20); text-shadow: 0 0 10px rgba(0, 255, 0, 0.8), 0 0 30px rgba(0, 255, 0, 0.4); }
        .red { color: rgb(247, 33, 25); text-shadow: 0 0 10px rgba(255, 0, 0, 1), 0 0 30px rgba(255, 0, 0, 1); }
        .blue{ color: rgb(57, 20, 255); text-shadow: 0 0 10px rgba(0, 0, 255, 0.8), 0 0 30px rgba(0, 0, 255, 0.4); }
        .purple {color: rgb(128, 0, 128);text-shadow: 0 0 10px rgba(128, 0, 128, 0.8), 0 0 30px rgba(128, 0, 128, 0.4);
    }
    </style>
        <h2 class="glowing">Admin Login</h2>
        <form method="post">
          <input type="password" name="password" placeholder="Password">
          <button type="submit">Login</button>
        </form>
    ''')

@app.route("/admin/panel", methods=["GET"])
def admin_panel():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    quiz_opts = "".join([f"<option value='{q}'>{q}</option>" for q in QUIZZES.keys()])
    html = '''
    <style>
        body {{ background-color: black; }}
        .glowing {{ text-shadow: 0 0 20px cyan, 0 0 25px cyan, 0 0 30px cyan; color: cyan; }}
        .green {{ color: rgb(57, 255, 20); text-shadow: 0 0 10px rgba(0, 255, 0, 0.8), 0 0 30px rgba(0, 255, 0, 0.4); }}
        .red {{ color: rgb(247, 33, 25); text-shadow: 0 0 10px rgba(255, 0, 0, 1), 0 0 30px rgba(255, 0, 0, 1); }}
        .blue {{ color: rgb(57, 20, 255); text-shadow: 0 0 10px rgba(0, 0, 255, 0.8), 0 0 30px rgba(0, 0, 255, 0.4); }}
        .purple {{ color: rgb(128, 0, 128); text-shadow: 0 0 10px rgba(128, 0, 128, 0.8), 0 0 30px rgba(128, 0, 128, 0.4); }}
    </style>

    <h2 class="glowing">Admin Panel</h2>
    <form method="post" action="/admin/create">
      <label class="green">Pick quiz:</label>
      <select name="quiz_name">{quiz_opts}</select>
      <label class="green">Number of 12-char access codes:</label>
      <input type="number" name="count" value="10" min="1">
      <button type="submit">Create Quiz</button>
    </form>

    <h3 class="glowing">Active Quizzes</h3>
    <table border=1 id="quiz-table">
      <tr class="green"><th>Quiz Name</th><th>6-digit Code</th><th>Players Joined</th></tr>
    </table>

    <h3>Stop Quiz</h3>
    <form method="post" action="/admin/stop">
      <input name="code" placeholder="Enter 6-digit code to stop">
      <button type="submit">Stop Quiz (kick all & download results)</button>
    </form>

    <script>
    async function update() {{
      let r = await fetch('/admin/data');
      let data = await r.json();
      let html = '<tr class="green"><th>Quiz Name</th><th>6-digit Code</th><th>Players Joined</th></tr>';
      for (let row of data) {{
        html += `<tr class="green"><td>${{row.name}}</td><td>${{row.code}}</td><td>${{row.count}}</td></tr>`;
      }}
      document.getElementById('quiz-table').innerHTML = html;
    }}
    setInterval(update, 1000);
    update();
    </script>
    '''.format(quiz_opts=quiz_opts)


    return render_template_string(html)

@app.route("/admin/create", methods=["POST"])
def admin_create():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    quiz_name = request.form.get("quiz_name")
    try:
        count = int(request.form.get("count", "10"))
    except:
        return "Invalid inputs", 400
    if quiz_name not in QUIZZES:
        return "Invalid quiz", 400
    six = str(secrets.randbelow(900000) + 100000)
    active_quizzes[six] = {
        "name": quiz_name,
        "joined_users": [],
        "sessions": set(),
        "answers": {}
    }

    new_codes = []
    for _ in range(count):
        while True:
            c12 = gen_12()
            if c12 not in codes:
                codes[c12] = {}
            if six not in codes[c12]:
                codes[c12][six] = {"used_by": None}
                new_codes.append(c12)
                break
    save_json(CODES_PATH, codes)
    tf = NamedTemporaryFile(mode="w+", delete=False, dir=APP_ROOT, prefix=f"{six}_codes_", suffix=".txt")
    try:
        tf.write("\n".join(new_codes))
        tf.flush(); tf.close()
        resp = send_file(tf.name, as_attachment=True, download_name=f"{six}_codes.txt")
    finally:
        try: os.remove(tf.name)
        except: pass
    return resp

@app.route("/admin/stop", methods=["POST"])
def admin_stop():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    code = request.form.get("code")
    if not code or code not in active_quizzes:
        return "Code not active", 400
    info = active_quizzes[code]
    quiz_name = info["name"]
    quiz_questions = QUIZZES[quiz_name]
    users_list = info["joined_users"]
    answers = info["answers"]
    answers_file = os.path.join(APP_ROOT, "answers.txt")
    correct_answers = []
    if os.path.exists(answers_file):
        with open(answers_file, encoding="utf8") as f:
            lines = [l.strip() for l in f if l.strip()]
        current = None
        for l in lines:
            if l.startswith("^"):
                current = l[1:].strip()
                continue
            correct_answers.append(l)
    else:
        correct_answers = [""] * len(quiz_questions)

    csv_path = os.path.join(APP_ROOT, "results.csv")
    existing = []
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf8") as f:
            existing = [l.strip() for l in f if l.strip()]

    header = ["Question No", "Correct Answer"] + [u["username"] + "/" + u["phone"] for u in users_list]

    focus_counts = {}
    focus_file = os.path.join(APP_ROOT, "focus.csv")
    if os.path.exists(focus_file):
        with open(focus_file, encoding="utf8") as f:
            lines = [l.strip().split(",") for l in f if l.strip() and not l.startswith("username")]
        for u in users_list:
            name = u["username"]
            cnt = sum(1 for row in lines if row[0] == name and row[2] == code)
            focus_counts[name] = cnt
    else:
        for u in users_list:
            focus_counts[u["username"]] = 0

    new_rows = []
    new_rows.append(",".join(["Quiz Code", code]))
    new_rows.append(",".join(header))

    fr = ["focus", ""]
    for u in users_list:
        fr.append(str(focus_counts[u["username"]]))
    new_rows.append(",".join(fr))

    for i, q in enumerate(quiz_questions, start=1):
        row = [str(i)]
        corr = correct_answers[i - 1] if i - 1 < len(correct_answers) else ""
        row.append(corr)
        for u in users_list:
            a = answers.get(u["phone"], {}).get(q["id"], "WRONG")
            if not a:
                a = "WRONG"
            row.append(a)
        new_rows.append(",".join(row))

    with open(csv_path, "a", encoding="utf8") as f:
        f.write("\n".join(new_rows) + "\n\n")

    for sid in list(sessions.keys()):
        s = sessions[sid]
        if s.get("quiz_code") == code:
            del sessions[sid]
    for c12 in list(codes.keys()):
        if code in codes[c12]:
            del codes[c12][code]
        if not codes[c12]:
            del codes[c12]
    save_json(CODES_PATH, codes)
    del active_quizzes[code]
    resp = send_file(csv_path, as_attachment=True, download_name=f"{code}_results.csv")
    try: os.remove(csv_path)
    except: pass
    return resp

@app.route("/admin/data", methods=["GET"])
def admin_data():
    out = []
    for code, info in list(active_quizzes.items()):
        out.append({"code": code, "name": info["name"], "count": len(info["joined_users"])})
    return jsonify(out)

@app.route("/login", methods=["POST"])
def login():
    j = request.get_json(silent=True) or {}
    username = j.get("username")
    phone = j.get("phone")
    if not username or not phone:
        return jsonify({"error": "missing"}), 400
    users[phone] = {"username": username, "phone": phone}
    save_json(USERS_PATH, users)
    return jsonify({"status": "ok"})

@app.route("/register", methods=["POST"])
def register():
    j = request.get_json(silent=True) or {}
    username = j.get("username"); phone = j.get("phone")
    six = j.get("quiz_code"); access = j.get("access_code")
    if not all([username, phone, six, access]):
        return jsonify({"error": "missing_fields"}), 400
    if six not in active_quizzes:
        return jsonify({"error": "invalid_quiz_code"}), 400
    if access not in codes or six not in codes[access]:
        return jsonify({"error": "invalid_access_code_for_quiz"}), 400
    if codes[access][six]["used_by"]:
        return jsonify({"error": "access_code_already_used"}), 403
    info = active_quizzes[six]
    codes[access][six]["used_by"] = username
    save_json(CODES_PATH, codes)
    sid = secrets.token_hex(16)
    sessions[sid] = {"username": username, "phone": phone, "quiz_code": six, "asked": set()}
    info["joined_users"].append({"username": username, "phone": phone})
    info["answers"][phone] = {}
    info["sessions"].add(sid)
    return jsonify({"session_id": sid})

@app.route("/get_question", methods=["POST"])
def get_question():
    j = request.get_json(silent=True) or {}
    sid = j.get("session_id")
    if not sid or sid not in sessions:
        return jsonify({"error": "invalid_session"}), 403
    s = sessions[sid]
    six = s["quiz_code"]
    quiz_name = active_quizzes[six]["name"]
    pool = QUIZZES[quiz_name]
    available = [q for q in pool if q["id"] not in s["asked"]]
    if not available:
        return jsonify({"done": True})
    q = secrets.choice(available)
    s["asked"].add(q["id"])
    exp = int(time.time() + QUESTION_EXPIRY)
    payload = {"qid": q["id"], "user": s["username"], "exp": exp}
    token = sign_payload(payload)
    s["last"] = payload
    return jsonify({"question": {"id": q["id"], "text": q["text"]}, "token": token, "exp": exp})

@app.route("/submit_answer", methods=["POST"])
def submit_answer():
    j = request.get_json(silent=True) or {}
    sid = j.get("session_id"); answer = j.get("answer"); token = j.get("token")
    if not sid or sid not in sessions:
        return jsonify({"error": "invalid_session"}), 403
    if not all([answer, token]):
        return jsonify({"error": "missing"}), 400
    s = sessions[sid]
    payload = s.get("last")
    if not payload or not verify_payload(payload, token):
        return jsonify({"error": "invalid_token"}), 403
    if time.time() > payload["exp"]:
        return jsonify({"error": "expired"}), 403
    six = s["quiz_code"]
    phone = s["phone"]
    qid = payload["qid"]
    active_quizzes[six]["answers"][phone][qid] = answer.strip()
    return jsonify({"status": "logged"})

@app.route("/ping", methods=["POST"])
def ping():
    j = request.get_json(silent=True) or {}
    username = j.get("username")
    code = j.get("code")
    if not username:
        return jsonify({"error": "missing"}), 400

    csv_path = os.path.join(APP_ROOT, "focus.csv")
    line = username + "," + str(int(time.time())) + "," + code

    exists = os.path.exists(csv_path)

    with open(csv_path, "a", encoding="utf8") as f:
        if not exists:
            f.write("username,timestamp,code\n")
        f.write(line + "\n")

    return jsonify({"status": "ok"})

@app.route("/admin/clear", methods=["POST", "GET"])
def clear():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    clear_file_contents(os.path.join(APP_ROOT, "focus.csv"))

if __name__ == "__main__":
    save_json(CODES_PATH, codes)
    save_json(USERS_PATH, users)
    save_json(RESULTS_PATH, results_data)
    app.run(host="0.0.0.0", port=5000)
