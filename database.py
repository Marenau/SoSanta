import sqlite3
from config import DATABASE

class Database:
    @staticmethod
    def init_db():
        """
        Инициализирует базу данных, создавая необходимые таблицы, если они еще не существуют.
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Таблица участников
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,  -- Уникальный идентификатор пользователя
                room_id TEXT,  -- Идентификатор комнаты
                first_name TEXT,  -- Имя пользователя
                last_name TEXT,  -- Фамилия пользователя
                wish TEXT,  -- Пожелание пользователя
                FOREIGN KEY (room_id) REFERENCES rooms (room_id)  -- Внешний ключ на таблицу rooms
            )
        ''')

        # Таблица назначений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                giver_id INTEGER,  -- Идентификатор дарителя
                receiver_id INTEGER,  -- Идентификатор получателя
                room_id INTEGER, -- Индентификатор комнаты
                FOREIGN KEY (giver_id) REFERENCES participants (user_id),  -- Внешний ключ на таблицу participants
                FOREIGN KEY (receiver_id) REFERENCES participants (user_id),  -- Внешний ключ на таблицу participants
                FOREIGN KEY (room_id) REFERENCES rooms (room_id) -- Внешний ключ на таблицу rooms
            )
        ''')

        # Таблица комнат
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rooms (
                room_id TEXT PRIMARY KEY,  -- Уникальный идентификатор комнаты
                name TEXT,  -- Название комнаты
                location_and_data TEXT, -- Место и время
                desc TEXT,  -- Описание комнаты
                status INTEGER DEFAULT 0,  -- Статус комнаты (по умолчанию 0)
                owner_id INTEGER  -- Идентификатор владельца комнаты
            )
        ''')

        # Таблица статистики
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id_stats INTEGER PRIMARY KEY,  -- Уникальный идентификатор статистики
                user_id INTEGER,  -- Идентификатор пользователя
                room_id INTEGER,  -- Идентификатор комнаты
                hit INTEGER,  -- Количество попаданий
                miss INTEGER,  -- Количество промахов
                FOREIGN KEY (user_id) REFERENCES participants (user_id),  -- Внешний ключ на таблицу participants
                FOREIGN KEY (room_id) REFERENCES rooms (room_id)  -- Внешний ключ на таблицу rooms
            )
        ''')

        # Таблица историй
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stories (
                id_story INTEGER PRIMARY KEY,  -- Уникальный идентификатор истории
                room_id INTEGER,  -- Идентификатор комнаты
                story_one TEXT,  -- Первая история
                story_two TEXT,  -- Вторая история
                story_three TEXT,  -- Третья история
                FOREIGN KEY (room_id) REFERENCES rooms (room_id)  -- Внешний ключ на таблицу rooms
            )
        ''')

        conn.commit()
        conn.close()

    @staticmethod
    def create_room(room_id, name, location_and_date, desc, owner_id):
        """
        Создает новую комнату.

        :param room_id: Уникальный идентификатор комнаты
        :param name: Название комнаты
        :param location_and_date: Дата и место проведения
        :param desc: Описание комнаты
        :param owner_id: Идентификатор владельца комнаты
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO rooms (room_id, name, location_and_data, desc, owner_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (room_id, name, location_and_date, desc, owner_id))
        conn.commit()
        conn.close()

    @staticmethod
    def add_participant(user_id, room_id, first_name, last_name, wish):
        """
        Добавляет нового участника в комнату.

        :param user_id: Уникальный идентификатор пользователя
        :param room_id: Идентификатор комнаты
        :param first_name: Имя пользователя
        :param last_name: Фамилия пользователя
        :param wish: Пожелание пользователя
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO participants (user_id, room_id, first_name, last_name, wish)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, room_id, first_name, last_name, wish))
        conn.commit()
        conn.close()

    @staticmethod
    def get_room(room_id):
        """
        Получает информацию о комнате по её идентификатору.

        :param room_id: Идентификатор комнаты
        :return: Информация о комнате
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM rooms WHERE room_id = ?
        ''', (room_id,))
        room = cursor.fetchone()
        conn.close()
        return room

    @staticmethod
    def remove_participant(user_id, room_id):
        """
        Удаляет участника из комнаты.

        :param user_id: Уникальный идентификатор пользователя
        :param room_id: Идентификатор комнаты
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM participants WHERE user_id = ? AND room_id = ?
        ''', (user_id, room_id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete_room(room_id):
        """
        Удаляет комнату и всех её участников.

        :param room_id: Идентификатор комнаты
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM rooms WHERE room_id = ?
        ''', (room_id,))
        cursor.execute('''
            DELETE FROM participants WHERE room_id = ?
        ''', (room_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def get_participants(room_id):
        """
        Получает список участников комнаты.

        :param room_id: Идентификатор комнаты
        :return: Список участников
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, first_name, last_name FROM participants WHERE room_id = ?
        ''', (room_id,))
        participants = cursor.fetchall()
        conn.close()
        return participants
    
    @staticmethod
    def get_user_rooms(user_id):
        """
        Получает список комнат, в которых участвует пользователь.

        :param user_id: Уникальный идентификатор пользователя
        :return: Список комнат
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.room_id, r.name, r.desc
            FROM participants p
            JOIN rooms r ON p.room_id = r.room_id
            WHERE p.user_id = ?
        ''', (user_id,))
        rooms = cursor.fetchall()
        conn.close()
        return rooms
    
    @staticmethod
    def update_wish(user_id, room_id, new_wish):
        """
        Обновляет желание участника.

        :param user_id: Уникальный идентификатор пользователя
        :param room_id: Идентификатор комнаты
        :param new_wish: Новое пожелание пользователя
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE participants
            SET wish = ?
            WHERE user_id = ? AND room_id = ?
        ''', (new_wish, user_id, room_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_wish(user_id, room_id):
        """
        Получает пожелание участника.

        :param user_id: Уникальный идентификатор пользователя
        :param room_id: Идентификатор комнаты
        :return: Пожелание участника
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT wish FROM participants WHERE user_id = ? AND room_id = ?
        ''', (user_id, room_id))
        wish = cursor.fetchone()
        conn.close()
        return wish[0] if wish else "Пожелание не найдено"
    
    @staticmethod
    def is_user_in_room(user_id, room_id=None):
        """
        Проверяет, присоединился ли пользователь к комнате.

        :param user_id: Уникальный идентификатор пользователя
        :param room_id: Идентификатор комнаты (опционально)
        :return: True, если пользователь присоединился к комнате, иначе False
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        if room_id:
            cursor.execute('''
                SELECT 1 FROM participants WHERE user_id = ? AND room_id = ?
            ''', (user_id, room_id))
        else:
            cursor.execute('''
                SELECT 1 FROM participants WHERE user_id = ?
            ''', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    @staticmethod
    def save_assignments(assignments):
        """
        Сохраняет назначения участников в базе данных.

        :param assignments: Список кортежей (giver_id, receiver_id)
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT INTO assignments (giver_id, receiver_id, room_id)
            VALUES (?, ?, ?)
        ''', assignments)
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_participant_by_id(user_id):
        """
        Получает информацию об участнике по его идентификатору.

        :param user_id: Идентификатор пользователя
        :return: Информация об участнике
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, first_name, last_name FROM participants WHERE user_id = ?
        ''', (user_id,))
        participant = cursor.fetchone()
        conn.close()
        return participant
    
    @staticmethod
    def set_room_active(room_id):
        """
        Устанавливает флаг активной игры в комнате.

        :param room_id: Идентификатор комнаты
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE rooms
            SET status = 1
            WHERE room_id = ?
        ''', (room_id,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_assignee(user_id, room_id):
        """
        Получает информацию о подопечном для участника.

        :param user_id: Идентификатор пользователя
        :param room_id: Идентификатор комнаты
        :return: Информация о подопечном
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.user_id, p.first_name, p.last_name
            FROM assignments a
            JOIN participants p ON a.receiver_id = p.user_id
            WHERE a.giver_id = ? AND a.room_id = ?
        ''', (user_id, room_id))
        assignee = cursor.fetchone()
        conn.close()
        return assignee

    @staticmethod
    def get_user_info(user_id):
        """
        Получает информацию о пользователе по его идентификатору.

        :param user_id: Идентификатор пользователя
        :return: Информация о пользователе
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT first_name, last_name, wish FROM participants WHERE user_id = ?', (user_id,))
        user_info = cursor.fetchone()
        conn.close()
        return user_info

    @staticmethod
    def get_user_name(user_id):
        """
        Получает имя пользователя по его идентификатору.

        :param user_id: Идентификатор пользователя
        :return: Имя пользователя
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT first_name, last_name FROM participants WHERE user_id = ?', (user_id,))
        user_name = cursor.fetchone()
        conn.close()
        return user_name

    @staticmethod
    def get_participant_count(room_code):
        """
        Получает количество участников в комнате.

        :param room_code: Идентификатор комнаты
        :return: Количество участников
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM participants WHERE room_id = ?', (room_code,))
        participant_count = cursor.fetchone()[0]
        conn.close()
        return participant_count
    
    @staticmethod
    def get_other_participants(user_id, target_user_id, room_code):
        """
        Получает список других участников, исключая текущего пользователя и целевого пользователя.

        :param user_id: Идентификатор текущего пользователя
        :param target_user_id: Идентификатор целевого пользователя
        :param room_code: Идентификатор комнаты
        :return: Список других участников
        """
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, first_name, last_name FROM participants WHERE user_id != ? AND user_id != ? AND room_id = ?', (user_id, target_user_id, room_code))
        other_participants = cursor.fetchall()
        conn.close()
        return other_participants