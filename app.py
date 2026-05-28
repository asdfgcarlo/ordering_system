from flask import Flask, render_template, request, redirect, session, flash, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
import hashlib

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'sql12.freesqldatabase.com'
app.config['MYSQL_USER'] = 'sql12828597'
app.config['MYSQL_PASSWORD'] = 'AKCsAQVCrD'
app.config['MYSQL_DB'] = 'sql12828597'

mysql = MySQL(app)

# ------------------ REGISTER ------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        account = cursor.fetchone()

        if account:
            flash("Email already exists!")
        else:
            # ✅ FIXED: include role
            cursor.execute(
                "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
                (username, email, hashed_password, 'user')
            )
            mysql.connection.commit()
            flash("Registration successful! Please login.")
            return redirect('/login')

    return render_template('register.html')


# ------------------ LOGIN ------------------
@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, hashed_password)
        )

        account = cursor.fetchone()

        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']

            # ✅ FIXED: safe role handling
            session['role'] = account.get('role', 'user')

            session['cart'] = []

            # ✅ ROLE-BASED REDIRECT
            if session['role'] == 'admin':
                return redirect('/admin')
            else:
                return redirect('/dashboard')

        else:
            flash("Invalid email or password!")

    return render_template('index.html')


# ------------------ DASHBOARD ------------------
@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session:
        return redirect('/login')

    return render_template('dashboard.html', username=session['username'])


# ------------------ ADMIN DASHBOARD ------------------
@app.route('/admin')
def admin_dashboard():
    if 'loggedin' not in session:
        return redirect('/login')

    if session.get('role') != 'admin':
        flash("Access denied: Admins only!")
        return redirect('/dashboard')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM sales ORDER BY created_at DESC")
    sales = cursor.fetchall()

    return render_template(
        'admin.html',
        username=session['username'],
        sales=sales
    )


# ------------------ ADD TO CART ------------------
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'loggedin' not in session:
        return jsonify({"error": "not logged in"}), 401

    if 'cart' not in session:
        session['cart'] = []

    data = request.json

    session['cart'].append({
        'item': data['item'],
        'price': float(data['price'])
    })

    session.modified = True

    return jsonify({"message": "added"})


# ------------------ CART PAGE ------------------
@app.route('/cart')
def cart():
    if 'loggedin' not in session:
        return redirect('/login')

    username = session['username']
    cart_items = session.get('cart', [])
    total = sum(item['price'] for item in cart_items)

    return render_template('cart.html', cart=cart_items, total=total, username=username)


# ------------------ BUY / CHECKOUT ------------------
@app.route('/buy', methods=['POST'])
def buy():
    if 'loggedin' not in session:
        return redirect('/login')

    cart = session.get('cart', [])

    if not cart:
        flash("Cart is empty!")
        return redirect('/cart')

    payment = request.form.get('payment')

    if not payment:
        flash("Select a payment method!")
        return redirect('/cart')

    username = session['username']

    item_bought = ", ".join([item['item'] for item in cart])
    total = sum(item['price'] for item in cart)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        INSERT INTO sales (username, item_bought, total, mode_of_payment)
        VALUES (%s, %s, %s, %s)
    """, (username, item_bought, total, payment))

    mysql.connection.commit()

    session['cart'] = []

    flash("Order placed successfully!")
    return redirect('/dashboard')


# ------------------ CLEAR CART ------------------
@app.route('/clear_cart')
def clear_cart():
    if 'loggedin' not in session:
        return redirect('/login')

    session['cart'] = []
    return redirect('/cart')


# ------------------ LOGOUT ------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True)