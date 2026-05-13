#!/usr/bin/env python3
"""
Главный файл запуска приложения
"""
import sys
import tkinter as tk
from local_db import init_local_db
from web_server import start_web_server
from gui_app import TransactionSearchApp

def main():
    # Инициализируем локальную БД
    init_local_db()
    
    # Запускаем веб-сервер в фоне
    start_web_server()
    
    # Запускаем GUI приложение
    root = tk.Tk()
    app = TransactionSearchApp(root)
    
    # Передаем в приложение информацию о текущем пользователе
    # (пока без авторизации, для обратной совместимости)
    app.current_user = None  # None = полный доступ (как раньше)
    
    root.mainloop()

if __name__ == "__main__":
    main()