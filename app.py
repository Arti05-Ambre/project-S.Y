from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# -------------------- PostgreSQL connection --------------------
conn = psycopg2.connect(
    host="localhost",
    database="scholarship_portal",
    user="postgres",
    password="123"
)
cur = conn.cursor()

# -------------------- Home --------------------
@app.route('/')
def index():
    return render_template('index.html')


# -------------------- Student Registration --------------------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        caste = request.form['caste']
        class_name = request.form['class_name']
        try:
            cur.execute(
                'INSERT INTO students (name,email,password,caste,class_name) VALUES (%s,%s,%s,%s,%s)',
                (name,email,password,caste,class_name)
            )
            conn.commit()
            return redirect(url_for('login'))
        except Exception as e:
            conn.rollback()
            return f"Error: {str(e)}"
    return render_template('register.html')


# -------------------- Student Login --------------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cur.execute('SELECT * FROM students WHERE email=%s', (email,))
        account = cur.fetchone()
        if account and check_password_hash(account[3], password):
            session['loggedin'] = True
            session['id'] = account[0]
            session['name'] = account[1]
            session['caste'] = account[4]
            session['class_name'] = account[5]
            return redirect(url_for('dashboard'))
        else:
            return "Invalid Credentials"
    return render_template('login.html')


# -------------------- Dashboard --------------------
@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cur.execute("SELECT * FROM scholarships")
    scholarships = cur.fetchall()

    # Simple notifications
    notifications = [f"Scholarship '{s[1]}' deadline: {s[4]}" for s in scholarships]

    return render_template(
        'dashboard.html',
        scholarships=scholarships,
        notifications=notifications
    )


# -------------------- Bookmark a scholarship --------------------
@app.route('/bookmark/<int:scholarship_id>')
def bookmark(scholarship_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cur.execute("""
        SELECT * FROM bookmarks 
        WHERE user_id=%s AND scholarship_id=%s
    """, (session['id'], scholarship_id))
    existing = cur.fetchone()

    if not existing:
        cur.execute("""
            INSERT INTO bookmarks (user_id, scholarship_id)
            VALUES (%s, %s)
        """, (session['id'], scholarship_id))
        conn.commit()

    return redirect(url_for('dashboard'))


# -------------------- View My Bookmarks --------------------
@app.route('/my_bookmarks')
def my_bookmarks():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cur.execute("""
        SELECT scholarships.name, scholarships.deadline
        FROM scholarships
        JOIN bookmarks ON scholarships.id = bookmarks.scholarship_id
        WHERE bookmarks.user_id = %s
    """, (session['id'],))
    data = cur.fetchall()
    return render_template('bookmarks.html', data=data)


# -------------------- Apply Scholarship --------------------
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/apply/<int:scholarship_id>', methods=['GET','POST'])
def apply_scholarship(scholarship_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files['document']
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            try:
                cur.execute(
                    'INSERT INTO applications (student_id, scholarship_id, document_submitted) VALUES (%s,%s,%s)',
                    (session['id'], scholarship_id, filename)
                )
                conn.commit()
                return "Application Submitted Successfully"
            except Exception as e:
                conn.rollback()
                return f"Error: {str(e)}"
    return render_template('apply_scholarship.html', scholarship_id=scholarship_id)


# -------------------- Admin Login --------------------
@app.route('/admin_login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur.execute('SELECT * FROM admin WHERE username=%s', (username,))
        account = cur.fetchone()
        if account and check_password_hash(account[2], password):
            session['admin_loggedin'] = True
            session['admin_name'] = account[1]
            return redirect(url_for('add_scholarship'))
        else:
            return "Invalid Admin Credentials"
    return render_template('admin_login.html')


# -------------------- Add Scholarship --------------------
@app.route('/add_scholarship', methods=['GET','POST'])
def add_scholarship():
    if 'admin_loggedin' not in session:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        name = request.form['name']
        caste = request.form['caste']
        class_name = request.form['class_name']
        deadline = request.form['deadline']
        description = request.form['description']
        try:
            cur.execute(
                'INSERT INTO scholarships (name,caste,class_name,deadline,description) VALUES (%s,%s,%s,%s,%s)',
                (name,caste,class_name,deadline,description)
            )
            conn.commit()
            return "Scholarship Added Successfully"
        except Exception as e:
            conn.rollback()
            return f"Error: {str(e)}"
    return render_template('add_scholarship.html')


# -------------------- Logout --------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# -------------------- Run App --------------------
if __name__ == '__main__':
    app.run(debug=True)
