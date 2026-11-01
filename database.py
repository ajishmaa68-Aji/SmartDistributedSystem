import sqlite3

def create_database():
    connection = sqlite3.connect("assignments.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            saved_status TEXT NOT NULL,
            FOREIGN KEY (assignment_id) REFERENCES assignments(id)
        )
    """)

    connection.commit()
    connection.close()

create_database()