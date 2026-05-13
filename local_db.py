import sqlite3
import hashlib
from datetime import datetime

def init_local_db():
    """Инициализация SQLite для хранения пользователей"""
    conn = sqlite3.connect('app_management.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Таблица прав на регионы
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_region_access (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            region_code TEXT,
            can_view BOOLEAN DEFAULT 1,
            can_export BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES app_users(id)
        )
    ''')
    
    # Таблица шаблонов запросов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            sql_template TEXT NOT NULL,
            parameters TEXT,  -- JSON
            created_by INTEGER,
            is_public BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES app_users(id)
        )
    ''')
    
    # Таблица логов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Создаем админа по умолчанию
    admin_exists = cursor.execute("SELECT id FROM app_users WHERE username = 'admin'").fetchone()
    if not admin_exists:
        password_hash = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute(
            "INSERT INTO app_users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            ("admin", password_hash, "Administrator", "admin")
        )
    
    conn.commit()
    conn.close()