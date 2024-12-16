import sqlite3
from cryptography.fernet import Fernet
from config import DATABASE

# Generate a key for encryption and decryption
key = Fernet.generate_key()
cipher_suite = Fernet(key)

def encrypt_wish(wish):
    return cipher_suite.encrypt(wish.encode())

def main():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Fetch all participants
    cursor.execute('SELECT user_id, wish FROM participants')
    participants = cursor.fetchall()

    for user_id, wish in participants:
        encrypted_wish = encrypt_wish(wish)
        cursor.execute('UPDATE participants SET wish = ? WHERE user_id = ?', (encrypted_wish, user_id))

    conn.commit()
    conn.close()
    print("All wishes have been encrypted.")

if __name__ == "__main__":
    main()
