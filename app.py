import os
import sqlite3
import secrets
from functools import wraps
from urllib.parse import urlparse

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]

DB_PATH = os.environ["DATABASE_PATH"]
ADMIN_USERNAME = os.environ["ADMIN_USERNAME"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
PUBLIC_BASE_URL = os.environ["PUBLIC_BASE_URL"]

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            target_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_links_code ON links(code)")
    db.commit()
    db.close()


def encode_base64_url(num: int) -> str:
    if num < 0:
        raise ValueError("num must be >= 0")
    if num == 0:
        return ALPHABET[0]

    base = len(ALPHABET)
    chars = []
    while num > 0:
        num, rem = divmod(num, base)
        chars.append(ALPHABET[rem])
    return "".join(reversed(chars))


def is_valid_code(code: str) -> bool:
    return bool(code) and all(ch in ALPHABET for ch in code)


def normalize_url(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        raise ValueError("URL is required")

    parsed = urlparse(raw)

    # if no scheme, assume https
    if not parsed.scheme:
        raw = "https://" + raw
        parsed = urlparse(raw)

    # only allow http and https
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https URLs are allowed")

    if not parsed.netloc:
        raise ValueError("Invalid URL")

    return raw


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("manage_login"))
        return view(*args, **kwargs)
    return wrapped


BASE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ title }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {
      font-family: system-ui, sans-serif;
      max-width: 980px;
      margin: 40px auto;
      padding: 0 16px;
      line-height: 1.4;
    }
    input[type=text], input[type=url], input[type=password] {
      width: 100%;
      padding: 10px;
      margin: 6px 0 14px;
      box-sizing: border-box;
    }
    button {
      padding: 10px 14px;
      cursor: pointer;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 20px;
    }
    th, td {
      border-bottom: 1px solid #ddd;
      padding: 10px;
      text-align: left;
      vertical-align: top;
    }
    .flash {
      padding: 10px 12px;
      margin-bottom: 16px;
      background: #f3f3f3;
      border-radius: 8px;
    }
    .nav {
      margin-bottom: 24px;
    }
    .nav a {
      margin-right: 12px;
    }
    .muted {
      color: #666;
    }
    code {
      background: #f5f5f5;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .row-actions form {
      display: inline-block;
      margin-right: 8px;
    }
  </style>
</head>
<body>
  <div class="nav">
    <a href="/">Home</a>
    {% if session.get("logged_in") %}
      <a href="/manage">Manage</a>
      <a href="/manage/logout">Logout</a>
    {% else %}
      <a href="/manage/login">Manage login</a>
    {% endif %}
  </div>

  {% with messages = get_flashed_messages() %}
    {% if messages %}
      {% for msg in messages %}
        <div class="flash">{{ msg }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  {{ content|safe }}
</body>
</html>
"""


@app.route("/")
def home():
    abort(404)
#def home():
#    content = """
#    <h1>urlshort</h1>
#    <p>Base64-url shortener with optional custom aliases.</p>
#    <p><a href="/manage">Go to manage</a></p>
#    """
#    return render_template_string(BASE_HTML, title="urlshort", content=content)


@app.route("/manage/login", methods=["GET", "POST"])
def manage_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            flash("Logged in.")
            return redirect(url_for("manage"))

        flash("Invalid credentials.")

    content = """
    <h1>Manage login</h1>
    <form method="post">
      <label>Username</label>
      <input type="text" name="username" required>

      <label>Password</label>
      <input type="password" name="password" required>

      <button type="submit">Login</button>
    </form>
    """
    return render_template_string(BASE_HTML, title="Login", content=content)


@app.route("/manage/logout")
def manage_logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for("manage_login"))


@app.route("/manage", methods=["GET", "POST"])
@login_required
def manage():
    db = get_db()

    if request.method == "POST":
        target_url = request.form.get("target_url", "")
        custom_code = request.form.get("custom_code", "").strip()

        try:
            target_url = normalize_url(target_url)
        except ValueError as e:
            flash(str(e))
            return redirect(url_for("manage"))

        if custom_code:
            if not is_valid_code(custom_code):
                flash("Custom code may only contain A-Z, a-z, 0-9, - and _")
                return redirect(url_for("manage"))

            exists = db.execute(
                "SELECT 1 FROM links WHERE code = ?",
                (custom_code,)
            ).fetchone()
            if exists:
                flash("That custom code is already taken.")
                return redirect(url_for("manage"))

            db.execute(
                "INSERT INTO links (code, target_url) VALUES (?, ?)",
                (custom_code, target_url)
            )
            db.commit()
            flash(f"Created custom short URL: {request.host_url}{custom_code}")
            return redirect(url_for("manage"))

        cur = db.execute(
            "INSERT INTO links (code, target_url) VALUES (?, ?)",
            ("__pending__", target_url)
        )
        new_id = cur.lastrowid
        code = encode_base64_url(new_id - 1)  # logical counter starts from 0

        db.execute(
            "UPDATE links SET code = ? WHERE id = ?",
            (code, new_id)
        )
        db.commit()

        flash(f"Created short URL: {PUBLIC_BASE_URL}{code}")
        return redirect(url_for("manage"))

    rows = db.execute(
        "SELECT id, code, target_url, created_at FROM links ORDER BY id DESC"
    ).fetchall()

    row_html = ""
    for row in rows:
        short_url = f"{PUBLIC_BASE_URL}{row['code']}"
        row_html += f"""
        <tr>
          <td>{row['id']}</td>
          <td>
            <code>{row['code']}</code><br>
            <a href="{short_url}" target="_blank">{short_url}</a>
          </td>
          <td style="max-width: 420px; word-break: break-all;">
            <a href="{row['target_url']}" target="_blank">{row['target_url']}</a>
          </td>
          <td>{row['created_at']}</td>
          <td class="row-actions">
            <form method="post" action="/manage/delete/{row['id']}" onsubmit="return confirm('Delete this link?');">
              <button type="submit">Delete</button>
            </form>
          </td>
        </tr>
        """

    content = f"""
    <h1>Manage links</h1>

    <h2>Create link</h2>
    <form method="post">
      <label>Target URL</label>
      <input type="url" name="target_url" placeholder="https://example.com/some/long/url" required>

      <label>Custom code (optional)</label>
      <input type="text" name="custom_code" placeholder="myAlias">

      <button type="submit">Create</button>
    </form>

    <p class="muted">
      Auto-generated codes use:
      <code>{ALPHABET}</code>
    </p>

    <h2>Existing links</h2>
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Short</th>
          <th>Destination</th>
          <th>Created</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {row_html or '<tr><td colspan="5">No links yet.</td></tr>'}
      </tbody>
    </table>
    """
    return render_template_string(BASE_HTML, title="Manage", content=content)


@app.route("/manage/delete/<int:link_id>", methods=["POST"])
@login_required
def delete_link(link_id: int):
    db = get_db()
    db.execute("DELETE FROM links WHERE id = ?", (link_id,))
    db.commit()
    flash("Link deleted.")
    return redirect(url_for("manage"))


@app.route("/<code>")
def redirect_code(code: str):
    if not is_valid_code(code):
        abort(404)

    db = get_db()
    row = db.execute(
        "SELECT target_url FROM links WHERE code = ?",
        (code,)
    ).fetchone()

    if not row:
        abort(404)

    return redirect(row["target_url"], code=302)


init_db()