from supabase import create_client
from flask import Flask, render_template, request, session, redirect, send_file
from openpyxl import Workbook

import sqlite3
import os
import base64

import cloudinary
import cloudinary.uploader
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = "BelgiumAttendance2026"
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)
ADMIN_USERNAME = "Jordan"
ADMIN_PASSWORD = "Belgium@TS"
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)
# Create signatures folder
os.makedirs("static/photos", exist_ok=True)

# Create database
conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    department TEXT,
    date TEXT,
    checkin_time TEXT,
    checkout_time TEXT,
    signature_file TEXT
)
""")

conn.commit()
conn.close()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/save', methods=['POST'])
def save():

    name = request.form['name'].strip()
    department = request.form['department']
    signature_data = request.form.get('photo_data', '')

    now = datetime.now(ZoneInfo("Asia/Kolkata"))

date = now.strftime("%d-%m-%Y")
checkin_time = now.strftime("%I:%M %p")

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM attendance
        WHERE LOWER(name)=LOWER(?)
        AND date=?
        """,
        (name, date)
    )

    existing = cursor.fetchone()

    if existing:

        conn.close()

        return f"""
        <html>
        <body style="font-family:Arial;text-align:center;margin-top:80px;">
        <h2 style="color:red;">Attendance Already Marked Today</h2>
        <p><b>{name}</b> has already checked in today.</p>
        <br><br>
        <a href="/">Back</a>
        </body>
        </html>
        """

    signature_filename = ""

    if signature_data:

        try:

            header, encoded = signature_data.split(",", 1)

            image_data = base64.b64decode(encoded)

            upload_result = cloudinary.uploader.upload(
                image_data,
                folder="attendance_photos"
            )

            signature_filename = upload_result["secure_url"]

        except Exception as e:
            print("Cloudinary Error:", e)

    cursor.execute(
        """
        INSERT INTO attendance
        (
            name,
            department,
            date,
            checkin_time,
            checkout_time,
            signature_file
        )
        VALUES (?,?,?,?,?,?)
        """,
        (
            name,
            department,
            date,
            checkin_time,
            "",
            signature_filename
        )
    )

    conn.commit()
    conn.close()

    return f"""
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:80px;">
        <h2>Attendance Saved Successfully</h2>
        <p><b>Name:</b> {name}</p>
        <p><b>Department:</b> {department}</p>
        <p><b>Check In:</b> {checkin_time}</p>
        <br><br>
        <a href="/">Back</a>
    </body>
    </html>
    """
        
@app.route('/checkout', methods=['POST'])
def checkout():

    name = request.form['name'].strip()

    checkout_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%I:%M %p")

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE attendance
        SET checkout_time = ?
        WHERE id = (
            SELECT id
            FROM attendance
            WHERE LOWER(name)=LOWER(?)
            ORDER BY id DESC
            LIMIT 1
        )
        """,
        (checkout_time, name)
    )

    conn.commit()
    conn.close()

    return f"""
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:80px;">

        <h2>Check Out Recorded Successfully</h2>

        <p><b>Name:</b> {name}</p>
        <p><b>Check Out:</b> {checkout_time}</p>

        <br><br>

        <a href="/">Back</a>

    </body>
    </html>
    """


@app.route('/admin')
def admin():

    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:100px;">

        <h2>Admin Login</h2>

        <form action="/login" method="POST">

            <input
            type="text"
            name="username"
            placeholder="Username"
            required
            style="padding:10px;width:250px;">

            <br><br>

            <input
            type="password"
            name="password"
            placeholder="Password"
            required
            style="padding:10px;width:250px;">

            <br><br>

            <button
            type="submit"
            style="
                padding:10px 20px;
                background:#0b5394;
                color:white;
                border:none;
                cursor:pointer;
            ">
                Login
            </button>

        </form>

    </body>
    </html>
    """


@app.route('/login', methods=['POST'])
def login():

    username = request.form.get('username')
    password = request.form.get('password')

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:

        session['admin_logged_in'] = True

        return redirect('/records')

    return """
    <html>
    <body style='font-family:Arial;text-align:center;margin-top:80px;'>

        <h2 style='color:red;'>Invalid Username or Password</h2>

        <br>

        <a href='/admin'>Back</a>

    </body>
    </html>
    """


@app.route('/records')
def records():

    if not session.get('admin_logged_in'):
        return redirect('/admin')

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        name,
        department,
        date,
        checkin_time,
        checkout_time,
        signature_file
    FROM attendance
    ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    today = datetime.now(
    ZoneInfo("Asia/Kolkata")
).strftime("%d-%m-%Y")

    present_today = sum(
        1 for row in rows
        if row[3] == today
    )

    checked_out = sum(
    1 for row in rows
    if row[3] == today and row[5]
)

    pending_checkout = sum(
        1 for row in rows
        if row[3] == today and not row[5]
    )

    conn.close()

    html = f"""
    <html>
    <head>

    <title>Attendance Records</title>

    <style>

    body{{
        font-family:Arial;
        padding:20px;
        background:#f4f6f9;
    }}

    .dashboard{{
        background:white;
        padding:20px;
        border-radius:10px;
        margin-bottom:20px;
        box-shadow:0px 0px 10px lightgray;
    }}

    .card{{
        display:inline-block;
        margin-right:20px;
        padding:15px;
        background:#eef4ff;
        border-radius:8px;
        min-width:180px;
        text-align:center;
    }}

    table{{
        border-collapse:collapse;
        width:100%;
        background:white;
    }}

    th,td{{
        border:1px solid #ccc;
        padding:10px;
        text-align:center;
    }}

    th{{
        background:#0b5394;
        color:white;
    }}

    img{{
        width:150px;
        border:1px solid #ccc;
    }}

    .logout{{
        background:red;
        color:white;
        padding:10px 15px;
        text-decoration:none;
        border-radius:5px;
        float:right;
    }}

    </style>

    </head>

    <body>

    <a
href="/export"
style="
background:green;
color:white;
padding:10px 15px;
text-decoration:none;
border-radius:5px;
margin-right:10px;
float:right;
">
Export Attendance
</a>

<a class="logout" href="/logout">Logout</a>

    <h2>Attendance Records</h2>

    <div class="dashboard">

        <div class="card">
            <h3>Present Today</h3>
            <h2>{present_today}</h2>
        </div>

        <div class="card">
            <h3>Checked Out</h3>
            <h2>{checked_out}</h2>
        </div>

        <div class="card">
            <h3>Pending Check Out</h3>
            <h2>{pending_checkout}</h2>
        </div>

    </div>

    <table>

    <tr>
        <th>ID</th>
        <th>Name</th>
        <th>Department</th>
        <th>Date</th>
        <th>Check In</th>
        <th>Check Out</th>
        <th>Selfie</th>
    </tr>
    """

    for row in rows:

        signature_html = "No Signature"

        if row[6]:
            signature_html = f'<img src="{row[6]}">'

        html += f"""
        <tr>
            <td>{row[0]}</td>
            <td>{row[1]}</td>
            <td>{row[2]}</td>
            <td>{row[3]}</td>
            <td>{row[4]}</td>
            <td>{row[5]}</td>
            <td>{signature_html}</td>
        </tr>
        """


    html += """
    </table>

    </body>
    </html>
    """

    return html


@app.route('/logout')
def logout():

    session.clear()

    return redirect('/admin')

@app.route('/export')
def export():

    if not session.get('admin_logged_in'):
        return redirect('/admin')

    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        name,
        department,
        date,
        checkin_time,
        checkout_time
    FROM attendance
    ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    wb = Workbook()

    ws = wb.active

    ws.title = "Attendance"

    ws.append([
        "ID",
        "Name",
        "Department",
        "Date",
        "Check In",
        "Check Out"
    ])

    for row in rows:
        ws.append(row)

    filename = "Attendance_Report.xlsx"

    wb.save(filename)

    return send_file(
        filename,
        as_attachment=True
    )
@app.route('/supabase-test')
def supabase_test():

    result = supabase.table("attendance").select("*").execute()

    return str(result.data)


if __name__ == '__main__':
    app.run(debug=True)
