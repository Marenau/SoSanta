import sqlite3
from config import DATABASE

def seed_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()


    # Добавление начальных данных в таблицу participants
    participants = [
        (1, 'wVm5CX3P', 'Иван', 'Иванов', 'Подарок 1'),
        (2, 'wVm5CX3P', 'Петр', 'Петров', 'Подарок 2'),
        (3, 'wVm5CX3P', 'Анна', 'Аннова', 'Подарок 3'),
        (4, 'wVm5CX3P', 'Мария', 'Маринова', 'Подарок 4'),
        (5, 'wVm5CX3P', 'Дмитрий', 'Дмитриев', 'Подарок 5'),
        (6, 'wVm5CX3P', 'Елена', 'Еленова', 'Подарок 6'),
    ]
    cursor.executemany('INSERT INTO participants (user_id, room_id, first_name, last_name, wish) VALUES (?, ?, ?, ?, ?)', participants)
    # Значения для обновления
    new_status = 1  # Новый статус
    room_id = 'wVm5CX3P'  # Идентификатор комнаты

    # Выполнение запроса
    cursor.execute('''
        UPDATE rooms
        SET status = ?
        WHERE room_id = ?
    ''', (new_status, room_id))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    seed_database()
