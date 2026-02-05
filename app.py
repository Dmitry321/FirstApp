from flask import Flask, jsonify, request
import sqlite3
import hashlib
import os
import dotenv
from functools import wraps
from flask_cors import CORS

API_TOKEN = os.getenv("API_TOKEN")

def require_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("Authorization")
        if token != f"Bearer {API_TOKEN}":
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

app=Flask(__name__)

#CORS(app, resources={
#    r"/products": {
#        "origins": ["*"], # Allows all origins - CHANGE THIS FOR PRODUCTION!
#        # Example for specific localhost port: "origins": ["http://localhost:5500"]
#        # Example for file:// access (less reliable): "origins": ["null"] or ["*"]
#    },
#    r"/register": { # Apply CORS to register endpoint as well
#        "origins": ["*"], # Allows all origins - CHANGE THIS FOR PRODUCTION!
#    }
#})

CORS(app, resources={
    r"/products": {
        "origins": ["*"], # Adjust for production
        "methods": ["GET"], # Explicitly state allowed methods
        "allow_headers": [] # No specific headers needed for GET usually
    },
    r"/register": { # Configure the /register endpoint
        "origins": ["*"], # Adjust for production - specify your web_client origin
        "methods": ["POST"], # Allow POST method
        "allow_headers": ["Content-Type", "X-Requested-With"] # Allow common headers for POST
    }
})

#products = [
#        {"id": 1, "name": "Keyboard", "price": 49.99},
#        {"id": 2, "name": "Mouse", "price": 29.99}
#   ]

def get_db_connection():
    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "products.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
   

def init_db():
    """Initialize the database and create tables if they don't exist."""
    print("Initializing Database...") # Log to Render logs
    conn = get_db_connection()
    try:
        # Create tables
        conn.execute('''CREATE TABLE IF NOT EXISTS products(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            price REAL NOT NULL
                        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS users(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT UNIQUE NOT NULL,
                            password TEXT NOT NULL
                        )''')
        conn.commit()
        print("Database tables ensured.") # Log to Render logs
    except Exception as e:
        print(f"Error during DB initialization: {e}") # Log error
        raise e # Re-raise to potentially cause a startup error if critical
    finally:
        conn.close()
        return jsonify({"message": "Database Inint complete"})
 
#@app.route("/init", methods=["GET"])
#def init_db():
#    conn = get_db_connection()
#    conn.execute("""
#                 CREATE TABLE IF NOT EXISTS products(
#                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
#                 name TEXT NOT NULL,
#                 price REAL NOT NULL
#                 )
#                 """)
#    conn.execute("""
#                 CREATE TABLE IF NOT EXISTS users(
#                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
#                 username TEXT UNIQUE NOT NULL,
#                 password TEXT NOT NULL
#                 )
#                 """)
#    conn.commit()
#    conn.close()
#    return jsonify({"message": "Database Inint complete"})

@app.route("/init", methods=["GET"]) # Optional: Keep this for manual checks if needed
def init_db_route():
    try:
        init_db() # Call the function
        return jsonify({"message": "Database Init via Route complete"})
    except Exception as e:
        return jsonify({"error": f"DB Init failed: {str(e)}"}), 500

# --- Initialize Database on Application Startup ---
# This runs when the app object is created, hopefully before the first request on Render
with app.app_context(): # Necessary to use application-specific contexts like g or current_app
    init_db()

@app.route("/")
def home():
    return jsonify({"message": "Hello from our first Flask Server!"})


@app.route("/products", methods=["GET"])
def get_products():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in rows])

@app.route("/products", methods=["POST"])
@require_token
def add_product():
    data = request.get_json()
    name = data.get("name")
    price = data.get("price")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (name, price) VALUES (?, ?)", (name, price))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    
    new_product = {
        "id": new_id,
        "name": name,
        "price": price
    }
#    products.append(new_product)
    return jsonify({"message": "Product added", "product": new_product}), 201

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400
    
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        conn.close()
        return jsonify({"message": "User register successfully"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 409
    
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400
    
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_password)).fetchone()
    conn.close()
    
    if user:
        return jsonify({"message": f"Welcome {username}!"})
    else:
        return jsonify({"error": "Invalid credentials"}), 401
    

#if __name__ == "__main__":
#    with app.app_context():
#        init_db()
#    app.run(debug=True)
