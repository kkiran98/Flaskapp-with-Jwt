from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
import atexit
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# In-memory user store for simplicity
users = {}

# Helper function to create JWT token
def create_token(username):
    payload = {
        'username': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

# Decorator to check for a valid JWT token
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 403
        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 403
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 403
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.form
        username = data.get('username')
        password = data.get('password')

        if username in users:
            return jsonify({'message': 'User already exists!'}), 400

        users[username] = password
        return redirect(url_for('home'))

    return render_template('signup.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.form
    username = data.get('username')
    password = data.get('password')

    if username in users and users[username] == password:
        token = create_token(username)
        return redirect(url_for('index', token=token))
    else:
        return jsonify({'message': 'Invalid credentials'}), 401

# SQLite database initialization
conn = sqlite3.connect('tasks.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT NOT NULL
    )
''')
conn.commit()

# Function to close the SQLite connection when the program exits
def close_database_connection():
    conn.close()

# Register the function to be called on exit
atexit.register(close_database_connection)

@app.route('/index')
@token_required
def index():
    token = request.args.get('token')
    # Fetch all tasks from the database
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks')
    tasks = cursor.fetchall()
    conn.close()
    return render_template('index.html', tasks=tasks, token=token)

@app.route('/add', methods=['POST'])
@token_required
def add_task():
    if request.method == 'POST':
        task_content = request.form['task']
        # Insert task into the database
        conn = sqlite3.connect('tasks.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO tasks (task) VALUES (?)', (task_content,))
        conn.commit()
        conn.close()
    token = request.args.get('token')
    return redirect(url_for('index', token=token))

@app.route('/delete/<int:task_id>', methods=['POST'])
@token_required
def delete_task(task_id):
    # Delete task from the database
    with sqlite3.connect('tasks.db') as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM tasks WHERE id=?', (task_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error deleting task: {e}")

    token = request.args.get('token')
    return redirect(url_for('index', token=token))

@app.route('/update/<int:task_id>', methods=['POST'])
@token_required
def update_task(task_id):
    if request.method == 'POST':
        updated_task_content = request.form['updated_task']
        # Update task in the database
        conn = sqlite3.connect('tasks.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE tasks SET task = ? WHERE id = ?', (updated_task_content, task_id))
        conn.commit()
        conn.close()
    token = request.args.get('token')
    return redirect(url_for('index', token=token))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8010)

