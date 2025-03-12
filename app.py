import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)
app.secret_key = "your_secret_key"  # Required for session management
bcrypt = Bcrypt(app)

# MySQL Configuration (XAMPP)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'rentify_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

mysql = MySQL(app)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Serve the main index page
@app.route('/')
def home():
    return render_template('index.html', logged_in=('user_id' in session))

# Serve the auth page
@app.route('/auth')
def auth_page():
    return render_template('auth.html')

# Admin Signup API
@app.route('/admin/signup', methods=['POST'])
def admin_signup():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    if not all([name, email, password]):
        return jsonify({'error': 'All fields are required'}), 400
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM admins WHERE email = %s", (email,))
    if cursor.fetchone():
        cursor.close()
        return jsonify({'error': 'Email already registered'}), 400
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    cursor.execute("INSERT INTO admins (name, email, password) VALUES (%s, %s, %s)", (name, email, hashed_password))
    mysql.connection.commit()
    cursor.close()
    
    return jsonify({'message': 'Admin signup successful', 'redirect': '/auth'}), 201  # Redirect to auth page after signup


# Admin Login API
@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not all([email, password]):
        return jsonify({'error': 'All fields are required'}), 400
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM admins WHERE email = %s", (email,))
    admin = cursor.fetchone()
    cursor.close()
    
    if admin and bcrypt.check_password_hash(admin['password'], password):
        session['admin_id'] = admin['id']
        session['admin_name'] = admin['name']
        return jsonify({'message': 'Login successful', 'redirect': '/admin_dashboard'}), 200
    else:
        return jsonify({'error': 'Invalid email or password'}), 401

# Admin Logout API
@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    return jsonify({'message': 'Logged out successfully', 'redirect': '/'}), 200

# Admin Dashboard
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('auth_page'))
    
    cursor = mysql.connection.cursor()
    
    # Fetch all users
    cursor.execute("SELECT id, name, email FROM users")
    users = cursor.fetchall()
    
    # Fetch categorized items with user names
    cursor.execute("""
    SELECT items.category, items.name, items.listed_date, items.rented, 
           users.name AS user_name, renters.name AS renter_name
    FROM items
    JOIN users ON items.user_id = users.id
    LEFT JOIN rentals ON items.id = rentals.item_id
    LEFT JOIN users AS renters ON rentals.user_id = renters.id
    ORDER BY items.category, items.listed_date
""")

    items = cursor.fetchall()
    cursor.close()
    
    categorized_items = {}
    for item in items:
        category = item['category']
        if category not in categorized_items:
            categorized_items[category] = []
        categorized_items[category].append(item)
    
    return render_template('admin_dashboard.html', admin_name=session['admin_name'], users=users, categorized_items=categorized_items)



# Serve the dashboard page with user-specific items
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    
    user_id = session['user_id']
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, name, category, price, image_url, rented FROM items WHERE user_id = %s", (user_id,))
    listed_items = cursor.fetchall()

    cursor.execute("""
        SELECT items.id, items.name, items.category, items.price, items.image_url, rentals.status 
        FROM rentals 
        JOIN items ON rentals.item_id = items.id 
        WHERE rentals.user_id = %s
    """, (user_id,))
    rented_items = cursor.fetchall()
    cursor.close()

    if request.headers.get('Accept') == 'application/json':
        return jsonify({'listed_items': listed_items, 'rented_items': rented_items})

    return render_template('dashboard.html', user_name=session['user_name'], listed_items=listed_items, rented_items=rented_items)

# API to check login status
@app.route('/api/check-login')
def check_login():
    return jsonify({'logged_in': 'user_id' in session})

# Serve dynamic pages
@app.route('/<page>')
def render_page(page):
    try:
        return render_template(f"{page}.html", logged_in=('user_id' in session))
    except:
        return "Page not found", 404

# Serve the login/signup page
@app.route('/login-page')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('log.html')

# Signup API
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    if not all([name, email, password]):
        return jsonify({'error': 'All fields are required'}), 400
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        cursor.close()
        return jsonify({'error': 'Email already registered'}), 400
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, hashed_password))
    mysql.connection.commit()
    cursor.close()
    
    return jsonify({'message': 'Signup successful'}), 201

# Login API
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not all([email, password]):
        return jsonify({'error': 'All fields are required'}), 400
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    
    if user and bcrypt.check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        return jsonify({'message': 'Login successful', 'redirect': '/'}), 200
    else:
        return jsonify({'error': 'Invalid email or password'}), 401

# Logout API
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    return jsonify({'message': 'Logged out successfully', 'redirect': '/'}), 200

# API to submit contact/feedback form
@app.route("/submit_contact", methods=["POST"])
def submit_contact():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    subject = data.get("subject")
    message = data.get("message")
    
    if not all([name, email, subject, message]):
        return jsonify({"message": "All fields are required!"}), 400
    
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO feedback (name, email, subject, message)
            VALUES (%s, %s, %s, %s)
        """, (name, email, subject, message))
        mysql.connection.commit()
        cursor.close()
        return jsonify({"message": "Feedback submitted successfully!"})
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"message": "Error saving feedback", "error": str(e)}), 500
    
# API to list an item
@app.route('/items', methods=['POST'])
def list_item():
    if 'user_id' not in session:
        return jsonify({'error': 'You must be logged in to list an item'}), 401  

    user_id = session['user_id']
    data = request.form
    image = request.files.get('image')

    if not data.get('item_name') or not data.get('category') or not data.get('description') or not data.get('price'):
        return jsonify({'error': 'All fields are required'}), 400

    if image:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(image.filename))
        image.save(image_path)
    else:
        image_path = None  # Allow listing without an image

    cursor = mysql.connection.cursor()
    query = """
        INSERT INTO items (name, category, description, price, image_url, user_id, listed_date)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
    """
    values = (data['item_name'], data['category'], data['description'], data['price'], image_path, user_id)
    
    cursor.execute(query, values)
    mysql.connection.commit()
    cursor.close()
    
    return jsonify({'success': True, 'message': 'Item listed successfully'})



# API to get available items
@app.route('/items', methods=['GET'])
def get_items():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT DISTINCT * FROM items WHERE rented = 0")  
    items = cursor.fetchall()
    cursor.close()
    
    return jsonify(items)

# API to rent an item
@app.route('/rent-item/<int:item_id>', methods=['POST'])
def rent_item(item_id):
    if 'user_id' not in session:
        return jsonify({'error': 'You must be logged in to rent an item'}), 401  

    user_id = session['user_id']
    cursor = mysql.connection.cursor()

    cursor.execute("SELECT * FROM items WHERE id = %s AND rented = 0", (item_id,))
    item = cursor.fetchone()
    
    if not item:
        return jsonify({'error': 'Item is not available or already rented'}), 400

    cursor.execute("UPDATE items SET rented = 1 WHERE id = %s", (item_id,))

    cursor.execute("INSERT INTO rentals (user_id, item_id, status) VALUES (%s, %s, 'rented')", (user_id, item_id))

    mysql.connection.commit()
    cursor.close()

    return jsonify({'success': True, 'message': 'Item rented successfully'})

# Rental details
@app.route('/rental-details/<int:item_id>')
def rental_details(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    cursor = mysql.connection.cursor()

    # Fetch rental details including rent date and return date
    cursor.execute("""
        SELECT items.id, items.name, items.category, items.image_url, 
               rentals.total_amount, rentals.duration, rentals.rent_date, rentals.return_date
        FROM rentals
        JOIN items ON rentals.item_id = items.id
        WHERE rentals.item_id = %s AND rentals.user_id = %s
    """, (item_id, user_id))
    
    rental = cursor.fetchone()
    cursor.close()

    if not rental:
        return "Rental details not found", 404

    return render_template('rental_details.html', rental=rental)


# Serve the payment page
@app.route('/payment', methods=['POST'])
def process_payment():
    if 'user_id' not in session:
        return jsonify({'error': 'You must be logged in to rent an item'}), 401  

    data = request.get_json()
    item_id = data.get('item_id')
    duration = int(data.get('duration'))  # Convert duration to integer
    total_amount = data.get('total_amount')
    user_id = session['user_id']

    if not item_id or not duration or not total_amount:
        return jsonify({'error': 'Invalid payment request'}), 400

    try:
        cursor = mysql.connection.cursor()
        
        # Ensure the item is available
        cursor.execute("SELECT * FROM items WHERE id = %s AND rented = 0", (item_id,))
        item = cursor.fetchone()
        if not item:
            return jsonify({'error': 'Item not available or already rented'}), 400

        # Calculate rent and return dates (without time)
        rent_date = datetime.today().date()  # Only date, no time
        return_date = rent_date + timedelta(days=duration)

        # Update item status to rented
        cursor.execute("UPDATE items SET rented = 1 WHERE id = %s", (item_id,))

        # Insert payment record with return date
        cursor.execute("""
            INSERT INTO rentals (user_id, item_id, duration, total_amount, rent_date, return_date, status) 
            VALUES (%s, %s, %s, %s, %s, %s, 'rented')
        """, (user_id, item_id, duration, total_amount, rent_date, return_date))

        mysql.connection.commit()
        cursor.close()

        return jsonify({'success': True, 'message': 'Payment successful, item rented', 'return_date': str(return_date)})

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
