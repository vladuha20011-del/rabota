import sqlite3
import hashlib
from typing import Optional, Dict, List
from app_config import REGIONS_FULL

class UserManager:
    @staticmethod
    def authenticate(username: str, password: str) -> Optional[Dict]:
        conn = sqlite3.connect('app_management.db')
        cursor = conn.cursor()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        user = cursor.execute(
            "SELECT id, username, full_name, role FROM app_users WHERE username = ? AND password_hash = ? AND is_active = 1",
            (username, password_hash)
        ).fetchone()
        conn.close()
        
        if user:
            return {"id": user[0], "username": user[1], "full_name": user[2], "role": user[3]}
        return None
    
    @staticmethod
    def get_user_regions(user_id: int) -> List[str]:
        conn = sqlite3.connect('app_management.db')
        cursor = conn.cursor()
        
        user_role = cursor.execute("SELECT role FROM app_users WHERE id = ?", (user_id,)).fetchone()
        
        if user_role and user_role[0] == "admin":
            regions = list(REGIONS_FULL.keys())
        else:
            regions = [
                row[0] for row in cursor.execute(
                    "SELECT region_code FROM user_region_access WHERE user_id = ? AND can_view = 1",
                    (user_id,)
                ).fetchall()
            ]
        conn.close()
        return regions
    
    @staticmethod
    def can_export(user_id: int, region_code: str) -> bool:
        conn = sqlite3.connect('app_management.db')
        cursor = conn.cursor()
        
        user_role = cursor.execute("SELECT role FROM app_users WHERE id = ?", (user_id,)).fetchone()
        
        if user_role and user_role[0] == "admin":
            conn.close()
            return True
        
        perm = cursor.execute(
            "SELECT can_export FROM user_region_access WHERE user_id = ? AND region_code = ?",
            (user_id, region_code)
        ).fetchone()
        conn.close()
        return perm is not None and perm[0]
    
    @staticmethod
    def log_activity(user_id: int, action: str, details: str, ip: str = ""):
        conn = sqlite3.connect('app_management.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO access_log (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)",
            (user_id, action, details, ip)
        )
        conn.commit()
        conn.close()