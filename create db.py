import sqlite3

def create_db():
    conn = sqlite3.connect('resumes.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY,
            name TEXT,
            salary TEXT,
            tags TEXT,
            employment TEXT,
            schedule TEXT
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_db()
