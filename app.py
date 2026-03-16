from flask import Flask, render_template, request, redirect, session
import mysql.connector
from datetime import date

app = Flask(__name__)
app.secret_key = "secret"

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1107",
    database="volunteer_system"
)

cursor = db.cursor(buffered=True)

# ── index ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    cursor.execute("SELECT COUNT(*) FROM volunteers")
    total_volunteers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM programs")
    total_programs = cursor.fetchone()[0]
    cursor.execute("SELECT COALESCE(SUM(hours),0) FROM attendance")
    total_hours = cursor.fetchone()[0]
    cursor.execute("""
        SELECT programs.program_name, COUNT(enrollments.volunteer_id) as enrolled
        FROM programs
        LEFT JOIN enrollments ON programs.program_id = enrollments.program_id
        GROUP BY programs.program_id
        ORDER BY programs.program_id DESC LIMIT 3
    """)
    recent_programs = cursor.fetchall()
    return render_template("index.html",
        total_volunteers=total_volunteers,
        total_programs=total_programs,
        total_hours=total_hours,
        recent_programs=recent_programs
    )

# ── auth ──────────────────────────────────────────────────────────────────────

@app.route("/login")
def login():
    cursor.execute("SELECT COUNT(*) FROM volunteers")
    total_volunteers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM programs")
    total_programs = cursor.fetchone()[0]
    cursor.execute("SELECT COALESCE(SUM(hours),0) FROM attendance")
    total_hours = cursor.fetchone()[0]
    return render_template("login.html",
        total_volunteers=total_volunteers,
        total_programs=total_programs,
        total_hours=total_hours
    )

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/register_user", methods=["POST"])
def register_user():
    if "first_name" in request.form:
        name = request.form["first_name"].strip() + " " + request.form["last_name"].strip()
    else:
        name = request.form["name"].strip()

    email    = request.form["email"].strip()
    phone    = request.form.get("phone", "").strip()
    password = request.form["password"]

    # Validation: check empty fields
    if not name or not email or not password:
        return redirect("/register?error=missing_fields")

    # Validation: duplicate email
    cursor.execute("SELECT volunteer_id FROM volunteers WHERE email=%s", (email,))
    if cursor.fetchone():
        return redirect("/register?error=email_taken")

    cursor.execute(
        "INSERT INTO volunteers (name, email, phone, password, status) VALUES (%s,%s,%s,%s,'pending')",
        (name, email, phone, password)
    )
    db.commit()
    return redirect("/login?success=registered")

@app.route("/login_user", methods=["POST"])
def login_user():
    email    = request.form["email"].strip()
    password = request.form["password"]
    role     = request.form["role"]

    if role == "admin":
        cursor.execute("SELECT * FROM admins WHERE email=%s AND password=%s", (email, password))
        admin = cursor.fetchone()
        if admin:
            session["admin"] = admin[1]
            return redirect("/admin_dashboard")
    else:
        cursor.execute("SELECT * FROM volunteers WHERE email=%s AND password=%s", (email, password))
        user = cursor.fetchone()
        if user:
            session["volunteer"]      = user[0]
            session["volunteer_name"] = user[1]
            return redirect("/volunteer_dashboard")

    return redirect("/login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ── admin dashboard ───────────────────────────────────────────────────────────

@app.route("/admin_dashboard")
def admin_dashboard():
    cursor.execute("SELECT COUNT(*) FROM volunteers")
    total_volunteers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM programs")
    total_programs = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(hours),0) FROM attendance")
    total_hours = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM attendance WHERE status='Present'")
    present = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM attendance")
    total_att = cursor.fetchone()[0]
    attendance_rate = round(present / total_att * 100) if total_att > 0 else 0

    # recent volunteers
    cursor.execute("SELECT name, email, status FROM volunteers ORDER BY volunteer_id DESC LIMIT 5")
    recent_volunteers = cursor.fetchall()

    # recent attendance
    cursor.execute("""
        SELECT volunteers.name, programs.program_name,
               attendance.status, attendance.hours, attendance.date
        FROM attendance
        JOIN volunteers ON attendance.volunteer_id = volunteers.volunteer_id
        JOIN programs   ON attendance.program_id   = programs.program_id
        ORDER BY attendance.attendance_id DESC LIMIT 5
    """)
    recent_attendance = cursor.fetchall()

    # programs capacity
    cursor.execute("SELECT program_id, program_name, max_volunteers FROM programs ORDER BY program_id DESC LIMIT 6")
    programs_capacity = cursor.fetchall()

    # enrollment counts per program
    cursor.execute("SELECT program_id, COUNT(*) FROM enrollments GROUP BY program_id")
    enrollment_counts = {row[0]: row[1] for row in cursor.fetchall()}

    return render_template(
        "admin_dashboard.html",
        total_volunteers=total_volunteers,
        total_programs=total_programs,
        total_hours=total_hours,
        attendance_rate=attendance_rate,
        recent_volunteers=recent_volunteers,
        recent_attendance=recent_attendance,
        programs_capacity=programs_capacity,
        enrollment_counts=enrollment_counts
    )

# ── volunteer dashboard ───────────────────────────────────────────────────────

@app.route("/volunteer_dashboard")
def volunteer_dashboard():
    volunteer_id = session.get("volunteer")

    cursor.execute("SELECT COALESCE(SUM(hours),0) FROM attendance WHERE volunteer_id=%s", (volunteer_id,))
    total_hours = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT program_id) FROM enrollments WHERE volunteer_id=%s", (volunteer_id,))
    total_programs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM attendance WHERE volunteer_id=%s AND status='Present'", (volunteer_id,))
    present = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM attendance WHERE volunteer_id=%s", (volunteer_id,))
    total_att = cursor.fetchone()[0]
    attendance_rate = round(present / total_att * 100) if total_att > 0 else 0

    cursor.execute("""
        SELECT programs.program_name, programs.date, programs.location,
               COALESCE(SUM(attendance.hours),0)
        FROM enrollments
        JOIN programs ON enrollments.program_id = programs.program_id
        LEFT JOIN attendance ON attendance.volunteer_id = %s
                             AND attendance.program_id  = programs.program_id
        WHERE enrollments.volunteer_id = %s
        GROUP BY programs.program_id
    """, (volunteer_id, volunteer_id))
    my_programs = cursor.fetchall()

    cursor.execute("""
        SELECT programs.program_name, attendance.status, attendance.hours, attendance.date
        FROM attendance
        JOIN programs ON attendance.program_id = programs.program_id
        WHERE attendance.volunteer_id = %s
        ORDER BY attendance.date DESC
        LIMIT 5
    """, (volunteer_id,))
    recent_activity = cursor.fetchall()

    # certs
    cursor.execute("""
        SELECT programs.program_name,
               COALESCE(SUM(attendance.hours), 0) AS hours,
               MAX(attendance.date) AS completed_date
        FROM enrollments
        JOIN programs ON enrollments.program_id = programs.program_id
        LEFT JOIN attendance ON attendance.volunteer_id = %s
                             AND attendance.program_id  = programs.program_id
        WHERE enrollments.volunteer_id = %s
        GROUP BY programs.program_id
        HAVING hours > 0
    """, (volunteer_id, volunteer_id))
    certs = cursor.fetchall()

    return render_template(
        "volunteer_dashboard.html",
        volunteer_name=session.get("volunteer_name", "Volunteer"),
        total_hours=total_hours,
        total_programs=total_programs,
        attendance_rate=attendance_rate,
        my_programs=my_programs,
        recent_activity=recent_activity,
        certs=certs
    )

# ── manage volunteers ─────────────────────────────────────────────────────────

@app.route("/manage_volunteers")
def manage_volunteers():
    cursor.execute("SELECT * FROM volunteers ORDER BY volunteer_id DESC")
    data = cursor.fetchall()
    total    = len(data)
    pending  = sum(1 for v in data if v[5] == 'pending')
    approved = sum(1 for v in data if v[5] == 'approved')
    rejected = sum(1 for v in data if v[5] == 'rejected')
    return render_template(
        "manage_volunteers.html",
        volunteers=data,
        total=total, pending=pending,
        approved=approved, rejected=rejected
    )

@app.route("/approve/<id>")
def approve(id):
    cursor.execute("UPDATE volunteers SET status='approved' WHERE volunteer_id=%s", (id,))
    db.commit()
    return redirect("/manage_volunteers")

@app.route("/reject/<id>")
def reject(id):
    cursor.execute("UPDATE volunteers SET status='rejected' WHERE volunteer_id=%s", (id,))
    db.commit()
    return redirect("/manage_volunteers")

# ── programs ──────────────────────────────────────────────────────────────────

@app.route("/programs")
def programs():
    cursor.execute("SELECT * FROM programs ORDER BY date ASC")
    all_programs = cursor.fetchall()

    volunteer_id = session.get("volunteer")
    cursor.execute("SELECT program_id FROM enrollments WHERE volunteer_id=%s", (volunteer_id,))
    enrolled_ids = {row[0] for row in cursor.fetchall()}

    cursor.execute("SELECT program_id, COUNT(*) FROM enrollments GROUP BY program_id")
    enrollment_counts = {row[0]: row[1] for row in cursor.fetchall()}

    return render_template(
        "programs.html",
        programs=all_programs,
        enrolled_ids=enrolled_ids,
        enrollment_counts=enrollment_counts
    )

@app.route("/enroll/<id>")
def enroll(id):
    volunteer_id = session.get("volunteer")
    cursor.execute(
        "SELECT enrollment_id FROM enrollments WHERE volunteer_id=%s AND program_id=%s",
        (volunteer_id, id)
    )
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO enrollments (volunteer_id, program_id, status) VALUES (%s,%s,'enrolled')",
            (volunteer_id, id)
        )
        db.commit()
    return redirect("/programs")

# ── create program ────────────────────────────────────────────────────────────

@app.route("/create_program")
def create_program():
    return render_template("create_program.html")

@app.route("/add_program", methods=["POST"])
def add_program():
    name        = request.form["name"]
    date_val    = request.form["date"]
    end_date    = request.form.get("end_date") or None
    time_start  = request.form.get("time_start") or None
    time_end    = request.form.get("time_end") or None
    location    = request.form["location"]
    description = request.form.get("description", "")
    max_vol     = request.form.get("max") or None
    category    = request.form.get("category") or None

    cursor.execute("""
        INSERT INTO programs
            (program_name, date, end_date, time_start, time_end, location, description, max_volunteers, category)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (name, date_val, end_date, time_start, time_end, location, description, max_vol, category))
    db.commit()
    return redirect("/admin_dashboard")

# ── attendance ────────────────────────────────────────────────────────────────

@app.route("/attendance")
def attendance():
    # get all enrollments with already saved attendance for today
    cursor.execute("""
        SELECT volunteers.name, programs.program_name,
               volunteers.volunteer_id, programs.program_id,
               attendance.status, attendance.hours
        FROM enrollments
        JOIN volunteers ON enrollments.volunteer_id = volunteers.volunteer_id
        JOIN programs   ON enrollments.program_id   = programs.program_id
        LEFT JOIN attendance ON attendance.volunteer_id = volunteers.volunteer_id
                             AND attendance.program_id  = programs.program_id
        ORDER BY programs.program_name, volunteers.name
    """)
    data = cursor.fetchall()
    cursor.execute("SELECT DISTINCT program_name FROM programs ORDER BY program_name")
    programs = cursor.fetchall()
    return render_template("attendance.html", data=data, programs=programs)

@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():
    volunteer = request.form["volunteer"]
    program   = request.form["program"]
    status    = request.form["status"]
    hours     = request.form.get("hours") or 0
    today     = date.today()

    cursor.execute("""
        INSERT INTO attendance (volunteer_id, program_id, date, status, hours)
        VALUES (%s,%s,%s,%s,%s)
    """, (volunteer, program, today, status, hours))
    db.commit()
    return redirect("/attendance")

# ── activity history ──────────────────────────────────────────────────────────

@app.route("/activity_history")
def activity_history():
    volunteer_id = session.get("volunteer")
    cursor.execute("""
        SELECT programs.program_name, attendance.status,
               attendance.hours, attendance.date
        FROM attendance
        JOIN programs ON attendance.program_id = programs.program_id
        WHERE attendance.volunteer_id = %s
        ORDER BY attendance.date DESC
    """, (volunteer_id,))
    data = cursor.fetchall()

    total_hours   = sum(r[2] for r in data if r[2] and r[1] == "Present")
    present_count = sum(1 for r in data if r[1] == "Present")
    total_att     = len(data)
    attendance_rate = round(present_count / total_att * 100) if total_att > 0 else 0

    cursor.execute("""
        SELECT DISTINCT programs.program_name
        FROM attendance
        JOIN programs ON attendance.program_id = programs.program_id
        WHERE attendance.volunteer_id = %s
    """, (volunteer_id,))
    program_list = cursor.fetchall()
    program_count = len(program_list)

    return render_template("activity_history.html",
        data=data,
        total_hours=total_hours,
        present_count=present_count,
        program_count=program_count,
        attendance_rate=attendance_rate,
        program_list=program_list
    )

# ── reports ───────────────────────────────────────────────────────────────────

@app.route("/reports")
def reports():
    cursor.execute("""
        SELECT volunteers.name,
               programs.program_name,
               COALESCE(SUM(attendance.hours), 0) AS hours,
               COUNT(CASE WHEN attendance.status='Present' THEN 1 END) AS present,
               COUNT(attendance.attendance_id) AS total_sessions
        FROM volunteers
        LEFT JOIN enrollments ON volunteers.volunteer_id = enrollments.volunteer_id
        LEFT JOIN programs    ON enrollments.program_id  = programs.program_id
        LEFT JOIN attendance  ON volunteers.volunteer_id = attendance.volunteer_id
        GROUP BY volunteers.volunteer_id, programs.program_id
        ORDER BY hours DESC
    """)
    volunteer_report = cursor.fetchall()

    cursor.execute("""
        SELECT programs.program_name,
               COUNT(DISTINCT enrollments.volunteer_id) AS enrolled,
               COALESCE(SUM(attendance.hours), 0)       AS total_hours,
               COUNT(CASE WHEN attendance.status='Present' THEN 1 END) AS present_count
        FROM programs
        LEFT JOIN enrollments ON programs.program_id = enrollments.program_id
        LEFT JOIN attendance  ON programs.program_id = attendance.program_id
        GROUP BY programs.program_id
        ORDER BY enrolled DESC
    """)
    program_report = cursor.fetchall()

    return render_template(
        "reports.html",
        volunteer_report=volunteer_report,
        program_report=program_report
    )

# ── feedback ──────────────────────────────────────────────────────────────────

@app.route("/feedback")
def feedback_page():
    cursor.execute("SELECT program_id, program_name FROM programs ORDER BY program_name")
    programs = cursor.fetchall()
    return render_template("feedback.html", programs=programs)

@app.route("/feedback", methods=["POST"])
def feedback():
    volunteer = session.get("volunteer")
    program   = request.form["program"]
    rating    = request.form.get("rating", 0)
    comment   = request.form.get("comment", "").strip()

    cursor.execute(
        "INSERT INTO feedback (volunteer_id, program_id, rating, comment) VALUES (%s,%s,%s,%s)",
        (volunteer, program, rating, comment)
    )
    db.commit()
    return redirect("/volunteer_dashboard")

# ── certificates ──────────────────────────────────────────────────────────────

@app.route("/certificates")
def certificates():
    volunteer_id = session.get("volunteer")

    cursor.execute("""
        SELECT programs.program_name,
               COALESCE(SUM(attendance.hours), 0) AS hours,
               MAX(attendance.date) AS completed_date
        FROM enrollments
        JOIN programs   ON enrollments.program_id  = programs.program_id
        LEFT JOIN attendance ON attendance.volunteer_id = %s
                             AND attendance.program_id  = programs.program_id
        WHERE enrollments.volunteer_id = %s
        GROUP BY programs.program_id
        HAVING hours > 0
    """, (volunteer_id, volunteer_id))
    certs = cursor.fetchall()

    return render_template(
        "certificates.html",
        certs=certs,
        volunteer_name=session.get("volunteer_name", "Volunteer")
    )

# ── run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)