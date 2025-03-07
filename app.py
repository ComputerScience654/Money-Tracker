from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# สร้าง database table ถ้ายังไม่มี-------------------------------------
def init_db():
    conn = sqlite3.connect('database.db', timeout=5)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,  -- "income" หรือ "expense"
            date TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

# Route หน้า Register-----------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            return "Passwords do not match", 400
        
        # บันทึกข้อมูลลง SQLite
        try:
            conn = sqlite3.connect('database.db', timeout=5)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, email, password)
                VALUES (?, ?, ?)
            ''', (username, email, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Username or Email already exists", 400
    return render_template('register.html')

# Route หน้า Login------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # ตรวจสอบข้อมูลผู้ใช้จากฐานข้อมูล
        conn = sqlite3.connect('database.db', timeout=5)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:  # ถ้าผู้ใช้มีในฐานข้อมูล
            session['user_id'] = user[0]  # เก็บ user_id ใน session
            return redirect(url_for('dashboard'))  # เปลี่ยนเส้นทางไปหน้า Dashboard
        else:
            error = "Invalid username or password"  # ส่งข้อความแสดงข้อผิดพลาด

    return render_template('index.html', error=error)  # แสดงฟอร์มล็อกอิน

# Route หน้า Dashboard-----------------------------------------------------
@app.route('/dashboard')
def dashboard():
    # เชื่อมต่อฐานข้อมูล
    conn = sqlite3.connect('database.db', timeout=5)
    cursor = conn.cursor()

    # คำนวณยอดรวมของรายรับและรายจ่าย
    cursor.execute('SELECT SUM(amount) FROM transactions WHERE type = "income"')
    total_income = cursor.fetchone()[0] or 0

    cursor.execute('SELECT SUM(amount) FROM transactions WHERE type = "expense"')
    total_expense = cursor.fetchone()[0] or 0

    balance = total_income - total_expense  # ยอดเงินคงเหลือ

    conn.close()

    return render_template('dashboard.html', balance=balance, total_income=total_income, total_expense=total_expense)

# Route สำหรับเพิ่มรายการธุรกรรม-----------------------------------------
@app.route('/add-transaction', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        name = request.form['name']
        amount = request.form['amount']
        transaction_type = request.form['type']
        date = request.form['date']

        # เชื่อมต่อฐานข้อมูลและบันทึกข้อมูล
        conn = sqlite3.connect('database.db', timeout=5)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (name, amount, type, date)
            VALUES (?, ?, ?, ?)
        ''', (name, amount, transaction_type, date))
        conn.commit()
        conn.close()

        return redirect(url_for('dashboard'))  # หลังจากบันทึกเสร็จจะกลับไปหน้า Dashboard

    return render_template('add_transaction.html')  # แสดงฟอร์มเพิ่มข้อมูล

@app.route('/transactions')
def transactions():
    filter_type = request.args.get('filter', 'all')

    # เชื่อมต่อฐานข้อมูล
    conn = sqlite3.connect('database.db', timeout=5)
    cursor = conn.cursor()

    # ดึงข้อมูลจากตาราง transactions ตาม filter
    if filter_type == 'income':
        cursor.execute('SELECT * FROM transactions WHERE type = "income" ORDER BY date DESC')
    elif filter_type == 'expense':
        cursor.execute('SELECT * FROM transactions WHERE type = "expense" ORDER BY date DESC')
    else:
        cursor.execute('SELECT * FROM transactions ORDER BY date DESC')

    transactions = cursor.fetchall()
    conn.close()

    # ส่งข้อมูลไปยัง template
    return render_template('transactions.html', transactions=transactions, filter=filter_type)

# Route หน้า Profile-----------------------------------------------------
@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    # เชื่อมต่อฐานข้อมูล
    conn = sqlite3.connect('database.db', timeout=5)
    cursor = conn.cursor()
    cursor.execute('SELECT username, email FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return "User not found", 404

    return render_template('profile.html', username=user[0], email=user[1])

# Route สำหรับ Logout-----------------------------------------------------
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # ลบ user_id จาก session
    return redirect(url_for('login'))  # เปลี่ยนเส้นทางไปหน้า Login

if __name__ == '__main__':
    init_db()  # สร้าง database table ก่อนเริ่มแอป
    app.run(debug=True)