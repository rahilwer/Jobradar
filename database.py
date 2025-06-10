import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('jobbot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # İstifadəçi cədvəli
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                selected_fields TEXT,
                notification_time TEXT DEFAULT '09:00',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Vakansiya cədvəli
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT,
                field TEXT,
                description TEXT,
                salary TEXT,
                location TEXT,
                contact TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Feedback cədvəli
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name):
        """Yeni istifadəçi əlavə et"""
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
            ''', (user_id, username, first_name))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"İstifadəçi əlavə edilərkən xəta: {e}")
            return False
    
    def update_user_fields(self, user_id, selected_fields):
        """İstifadəçinin seçdiyi sahələri yenilə"""
        fields_json = json.dumps(selected_fields)
        try:
            self.cursor.execute('''
                UPDATE users SET selected_fields = ? WHERE user_id = ?
            ''', (fields_json, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Sahələr yenilənərkən xəta: {e}")
            return False
    
    def get_user_fields(self, user_id):
        """İstifadəçinin seçdiyi sahələri gətir"""
        self.cursor.execute('SELECT selected_fields FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        if result and result[0]:
            return json.loads(result[0])
        return []
    
    def get_users_by_field(self, field):
        """Müəyyən sahəni seçən istifadəçiləri gətir"""
        self.cursor.execute('SELECT user_id, selected_fields FROM users WHERE is_active = 1')
        users = []
        for row in self.cursor.fetchall():
            if row[1]:
                fields = json.loads(row[1])
                if field in fields:
                    users.append(row[0])
        return users
    
    def add_job(self, title, company, field, description, salary, location, contact):
        """Yeni vakansiya əlavə et"""
        try:
            self.cursor.execute('''
                INSERT INTO jobs (title, company, field, description, salary, location, contact)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, company, field, description, salary, location, contact))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Vakansiya əlavə edilərkən xəta: {e}")
            return None
    
    def get_recent_jobs(self, field=None, limit=10):
        """Son vakansiyaları gətir"""
        if field:
            self.cursor.execute('''
                SELECT * FROM jobs WHERE field = ? AND is_active = 1 
                ORDER BY created_at DESC LIMIT ?
            ''', (field, limit))
        else:
            self.cursor.execute('''
                SELECT * FROM jobs WHERE is_active = 1 
                ORDER BY created_at DESC LIMIT ?
            ''', (limit,))
        return self.cursor.fetchall()
    
    def add_feedback(self, user_id, message):
        """Feedback əlavə et"""
        try:
            self.cursor.execute('''
                INSERT INTO feedback (user_id, message)
                VALUES (?, ?)
            ''', (user_id, message))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Feedback əlavə edilərkən xəta: {e}")
            return False
    
    def set_notification_time(self, user_id, time):
        """İstifadəçinin bildiriş vaxtını təyin et"""
        try:
            self.cursor.execute('''
                UPDATE users SET notification_time = ? WHERE user_id = ?
            ''', (time, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Bildiriş vaxtı təyin edilərkən xəta: {e}")
            return False
    
    def get_all_active_users(self):
        """Bütün aktiv istifadəçiləri gətir"""
        self.cursor.execute('SELECT user_id FROM users WHERE is_active = 1')
        return [row[0] for row in self.cursor.fetchall()]
    
    def close(self):
        """Verilənlər bazası bağlantısını bağla"""
        self.conn.close()