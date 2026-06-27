from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import sqlite3
import os
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import requests

app = Flask(__name__)
app.secret_key = os.urandom(24)

DATABASE_PATH = r"C:\Users\BCS\Desktop\Chashman csv\database.sqlite3 "
CSV_PATH = "static/data.csv"

# ⚙️ Setup SQLite database for users
def setup_user_table():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

setup_user_table()

# ✅ Load CSV and prepare FAISS index
def load_data():
    df = pd.read_csv(CSV_PATH)
    questions = df["Question"].tolist()
    answers = df["Answer"].tolist()
    return questions, answers

questions, answers = load_data()
model = SentenceTransformer("all-MiniLM-L6-v2")
question_embeddings = model.encode(questions)
dimension = question_embeddings[0].shape[0]
index = faiss.IndexFlatL2(dimension)
index.add(np.array(question_embeddings))

def get_best_match_response(user_input):
    user_embedding = model.encode([user_input])
    D, I = index.search(np.array(user_embedding), k=1)
    best_index = I[0][0]
    score = D[0][0]
    if score > 1.5:
        return "Sorry, I couldn't find a relevant answer."
    return answers[best_index]

def translate_text(text, target_lang):
    if target_lang == "en":
        return text
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "en",
        "tl": target_lang,
        "dt": "t",
        "q": text
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()[0][0][0]
    return text

# ✅ Load all or filtered campus images
def load_gallery_images(filter_keywords=None):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, image_filename FROM campus_gallery")
    rows = cursor.fetchall()
    conn.close()

    images = []
    for name, filename in rows:
        if filter_keywords:
            for keyword in filter_keywords:
                if keyword.lower() in name.lower():
                    images.append({
                        "name": name,
                        "image": url_for('static', filename=f"gallery/{filename}")
                    })
                    break
        else:
            images.append({
                "name": name,
                "image": url_for('static', filename=f"gallery/{filename}")
            })
    return images

# 👩‍🏫 Load faculty profiles based on department or subject keywords
def load_faculty_images(filter_keywords=None):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, title, email, image_filename FROM faculty_members")
    rows = cursor.fetchall()
    conn.close()

    faculty = []
    for name, title, email, filename in rows:
        if filter_keywords:
            for keyword in filter_keywords:
                if (keyword.lower() in name.lower()
                    or keyword.lower() in title.lower()
                    or keyword.lower() in email.lower()
                    or keyword.lower() in filename.lower()):
                    faculty.append({
                        "name": name,
                        "title": title,
                        "email": email,
                        "image": url_for('static', filename=f"faculty/{filename}")
                    })
                    break
        else:
            faculty.append({
                "name": name,
                "title": title,
                "email": email,
                "image": url_for('static', filename=f"faculty/{filename}")
            })
    return faculty

# 🔐 User Registration
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return "Username already exists! Please choose another one."

        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        conn.close()

        return redirect(url_for("login"))
    return render_template("signup.html")

# 🔐 User Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            return redirect(url_for("home"))
        return "Invalid username or password. Please try again."

    return render_template("login.html")

# 🔒 Logout
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))

# 🏠 Home Page
@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

# 🤖 Chat API
@app.route("/chat", methods=["POST"])
def chat():
    if "user_id" not in session:
        return jsonify({"response": "Unauthorized access. Please log in."})

    data = request.get_json()
    message = data.get("message", "")
    language = data.get("language", "en")

    message_words = message.lower().split()

    # Faculty logic
    faculty_keywords = ["faculty", "professor", "lecturer", "teacher", "department", "hod"]
    if any(word in message.lower() for word in faculty_keywords):
        faculty = load_faculty_images(filter_keywords=message_words)
        if faculty:
            response_text = "Here are the faculty members you asked about:"
        else:
            response_text = "Sorry, I couldn’t find any faculty information matching your request."
        translated_response = translate_text(response_text, language)
        return jsonify({"response": translated_response, "faculty": faculty})

    # Gallery logic
    gallery_keywords = ["campus", "photo", "picture", "gallery", "image", "show me", "see"]
    if any(word in message.lower() for word in gallery_keywords):
        images = load_gallery_images(filter_keywords=message_words)
        if images:
            response_text = "Here are some photos of our university:"
        else:
            response_text = "Sorry, I couldn't find any photos matching your request."
        translated_response = translate_text(response_text, language)
        return jsonify({"response": translated_response, "images": images})

    response = get_best_match_response(message)
    translated_response = translate_text(response, language)
    return jsonify({"response": translated_response})

# 🔄 Reload CSV and FAISS index
@app.route("/reload", methods=["GET"])
def reload_data():
    global questions, answers, question_embeddings, index
    questions, answers = load_data()
    question_embeddings = model.encode(questions)
    index = faiss.IndexFlatL2(question_embeddings[0].shape[0])
    index.add(np.array(question_embeddings))
    return jsonify({"status": "Data reloaded successfully!"})

if __name__ == "__main__":
    app.run(debug=True)
