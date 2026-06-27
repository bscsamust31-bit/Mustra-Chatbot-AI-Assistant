import sqlite3
import os

# === Config ===
GALLERY_FOLDER = r"C:\Users\BCS\Desktop\Chashman csv\static\gallery"
FACULTY_FOLDER = r"C:\Users\BCS\Desktop\Chashman csv\static\faculty"
DATABASE_PATH = r"C:\Users\BCS\Desktop\Chashman csv\database.sqlite3"

# === Correct faculty filename-to-metadata mapping ===
faculty_data = {
    "faculty_Aasim_Ali.png": ("Dr. Aasim Ali", "HOD Computing & IT", "hod.cs@multanust.edu.pk"),
    "faculty_Amanullah_Khan.png": ("Dr. Aman Ullah", "Professor", "aman.ullah@multanust.edu.pk"),
    "faculty_Adnan_Alvi.png": ("Dr. Adnan Alvi", "Assistant Professor", "adnan.alvi@multanust.edu.pk"),
    "faculty_Mueez_Amin.png": ("Mr. Mueez Amin", "Lecturer", "muhammad.mueez@multanust.edu.pk"),
    "faculty_Salman_Ayub.png": ("Mr. Salman Ayub Khan", "Lecturer", "salman.khan@multanust.edu.pk"),
    "faculty_Naveed_Akhter.png": ("Mr. Naveed Akhter", "Lecturer", "naveed.akhter@multanust.edu.pk"),
    "faculty_Zeeshan_Ali.png": ("Mr. Muhammad Zeeshan", "Lecturer", "muhammad.zeeshan@multanust.edu.pk")
}

# === Create tables if not exist ===
def create_gallery_table():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS faculty_members")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faculty_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            title TEXT,
            email TEXT,
            image_filename TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campus_gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            image_filename TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

# === Insert image entries ===
def insert_images_from_folder():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Insert gallery images
    for filename in os.listdir(GALLERY_FOLDER):
        if filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
            name = os.path.splitext(filename)[0].replace("_", " ").title()
            cursor.execute("SELECT * FROM campus_gallery WHERE image_filename = ?", (filename,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO campus_gallery (name, image_filename) VALUES (?, ?)", (name, filename))
                print(f"Inserted Gallery: {name} -> {filename}")

    # Insert faculty images
    for filename, (name, title, email) in faculty_data.items():
        if os.path.exists(os.path.join(FACULTY_FOLDER, filename)):
            cursor.execute("SELECT * FROM faculty_members WHERE image_filename = ?", (filename,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO faculty_members (name, title, email, image_filename)
                    VALUES (?, ?, ?, ?)
                """, (name, title, email, filename))
                print(f"Inserted Faculty: {name} -> {filename}")
        else:
            print(f"❌ Missing file: {filename} in faculty folder.")

    conn.commit()
    conn.close()
    print("✅ All done!")

# === Run it ===
if __name__ == "__main__":
    create_gallery_table()
    insert_images_from_folder()
