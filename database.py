import sqlite3
from config import DATABASE

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            user_id INTEGER PRIMARY KEY,
            room_id TEXT,
            first_name TEXT,
            last_name TEXT,
            wish TEXT,
            FOREIGN KEY (room_id) REFERENCES rooms (room_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            giver_id INTEGER,
            receiver_id INTEGER,
            FOREIGN KEY (giver_id) REFERENCES participants (user_id),
            FOREIGN KEY (receiver_id) REFERENCES participants (user_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            room_id TEXT PRIMARY KEY,
            name TEXT,
            desc TEXT,
            status INTEGER DEFAULT 0,
            owner_id INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            id_stats INTEGER PRIMARY KEY,
            user_id INTEGER,
            room_id INTEGER,
            hit INTEGER,
            miss INTEGER,
            FOREIGN KEY (user_id) REFERENCES participants (user_id),
            FOREIGN KEY (room_id) REFERENCES rooms (room_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stories (
            id_story INTEGER PRIMARY KEY,
            room_id INTEGER,
            story_one TEXT,
            story_two TEXT,
            story_three TEXT,
            FOREIGN KEY (room_id) REFERENCES rooms (room_id)
        )
    ''')
    conn.commit()
    conn.close()

def add_participant(user_id, room_id, first_name, last_name, wish):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO participants (user_id, room_id, first_name, last_name, wish) VALUES (?, ?, ?, ?, ?)',
                   (user_id, room_id, first_name, last_name, wish))
    conn.commit()
    conn.close()

def get_participant(user_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name, wish FROM participants WHERE user_id = ?', (user_id,))
    user_info = cursor.fetchone()
    conn.close()
    return user_info

def get_all_participants():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name FROM participants')
    participants = cursor.fetchall()
    conn.close()
    return participants

def get_participants_by_room(room_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT first_name, last_name FROM participants WHERE room_id = ?', (room_id,))
    participants = cursor.fetchall()
    conn.close()
    return participants

def update_participant_wish(user_id, wish):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('UPDATE participants SET wish = ? WHERE user_id = ?', (wish, user_id))
    conn.commit()
    conn.close()

def delete_participant(user_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM participants WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def clear_participants():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM participants')
    cursor.execute('DELETE FROM assignments')
    cursor.execute('UPDATE rooms SET status = "not_started"')
    conn.commit()
    conn.close()

def add_room(room_id, name, desc, owner_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO rooms (room_id, name, desc, owner_id) VALUES (?, ?, ?, ?)', (room_id, name, desc, owner_id))
    conn.commit()
    conn.close()

def get_room(room_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM rooms WHERE room_id = ?', (room_id,))
    room = cursor.fetchone()
    conn.close()
    return room

def delete_room(room_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM rooms WHERE room_id = ?', (room_id,))
    cursor.execute('DELETE FROM participants WHERE room_id = ?', (room_id,))
    conn.commit()
    conn.close()

def start_room_game(room_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, first_name, last_name, wish FROM participants WHERE room_id = ?', (room_id,))
    participants = cursor.fetchall()
    if len(participants) < 3:
        conn.close()
        return False

    participants = [(row[0], row[1], row[2], row[3]) for row in participants]
    random.shuffle(participants)
    assignments = []
    for i in range(len(participants)):
        giver = participants[i]
        receiver = participants[(i + 1) % len(participants)]
        assignments.append((giver[0], receiver[0]))

    cursor.execute('DELETE FROM assignments WHERE giver_id IN (SELECT user_id FROM participants WHERE room_id = ?) OR receiver_id IN (SELECT user_id FROM participants WHERE room_id = ?)', (room_id, room_id))
    cursor.executemany('INSERT INTO assignments (giver_id, receiver_id) VALUES (?, ?)', assignments)
    cursor.execute('UPDATE rooms SET status = "started" WHERE room_id = ?', (room_id,))
    conn.commit()
    conn.close()
    return True

def get_assignments(room_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT giver_id, receiver_id FROM assignments WHERE giver_id IN (SELECT user_id FROM participants WHERE room_id = ?) OR receiver_id IN (SELECT user_id FROM participants WHERE room_id = ?)', (room_id, room_id))
    assignments = cursor.fetchall()
    conn.close()
    return assignments

def get_room_status(room_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT status FROM rooms WHERE room_id = ?', (room_id,))
    status = cursor.fetchone()[0]
    conn.close()
    return status

def get_room_id_by_user(user_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT room_id FROM participants WHERE user_id = ?', (user_id,))
    room_id = cursor.fetchone()
    conn.close()
    return room_id[0] if room_id else None
