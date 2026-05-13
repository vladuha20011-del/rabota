# gui_windows.py
# Дополнительные окна: управление пользователями, управление запросами

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import hashlib
from app_config import REGIONS_FULL

class UserManagementWindow:
    """Окно для управления пользователями и правами"""
    
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Управление пользователями")
        self.window.geometry("900x650")
        self.window.configure(bg='white')
        
        self.create_widgets()
        self.load_users()
    
    def create_widgets(self):
        # Список пользователей
        self.user_tree = ttk.Treeview(self.window, columns=('ID', 'Логин', 'ФИО', 'Роль', 'Активен'), 
                                      show='headings', height=15)
        self.user_tree.heading('ID', text='ID', width=40)
        self.user_tree.heading('Логин', text='Логин', width=150)
        self.user_tree.heading('ФИО', text='ФИО', width=200)
        self.user_tree.heading('Роль', text='Роль', width=80)
        self.user_tree.heading('Активен', text='Активен', width=70)
        self.user_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.user_tree.bind('<Double-1>', self.on_user_double_click)
        
        # Кнопки
        btn_frame = tk.Frame(self.window, bg='white')
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="➕ Добавить пользователя", command=self.add_user,
                 bg='#28a745', fg='white', font=('Segoe UI', 10, 'bold'),
                 relief='flat', padx=15, pady=5, cursor='hand2').pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="🔑 Редактировать права", command=self.edit_permissions,
                 bg='#4a86e8', fg='white', font=('Segoe UI', 10, 'bold'),
                 relief='flat', padx=15, pady=5, cursor='hand2').pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="❌ Удалить", command=self.delete_user,
                 bg='#dc3545', fg='white', font=('Segoe UI', 10, 'bold'),
                 relief='flat', padx=15, pady=5, cursor='hand2').pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="Закрыть", command=self.window.destroy,
                 bg='#6c757d', fg='white', font=('Segoe UI', 10, 'bold'),
                 relief='flat', padx=15, pady=5, cursor='hand2').pack(side=tk.LEFT, padx=5)
    
    def load_users(self):
        """Загрузка списка пользователей"""
        conn = sqlite3.connect('app_management.db')
        cursor = conn.cursor()
        users = cursor.execute("SELECT id, username, full_name, role, is_active FROM app_users").fetchall()
        conn.close()
        
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)
        
        for user in users:
            active_text = "Да" if user[4] else "Нет"
            self.user_tree.insert('', tk.END, values=(user[0], user[1], user[2], user[3], active_text))
    
    def on_user_double_click(self, event):
        """Двойной клик - редактирование прав"""
        self.edit_permissions()
    
    def add_user(self):
        """Диалог добавления пользователя"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Добавить пользователя")
        dialog.geometry("400x350")
        dialog.configure(bg='white')
        dialog.transient(self.window)
        dialog.grab_set()
        
        tk.Label(dialog, text="Логин:", bg='white', font=('Segoe UI', 10)).pack(pady=(20, 5))
        username = tk.Entry(dialog, font=('Segoe UI', 10), width=30)
        username.pack()
        
        tk.Label(dialog, text="Пароль:", bg='white', font=('Segoe UI', 10)).pack(pady=(10, 5))
        password = tk.Entry(dialog, show="*", font=('Segoe UI', 10), width=30)
        password.pack()
        
        tk.Label(dialog, text="ФИО:", bg='white', font=('Segoe UI', 10)).pack(pady=(10, 5))
        full_name = tk.Entry(dialog, font=('Segoe UI', 10), width=30)
        full_name.pack()
        
        tk.Label(dialog, text="Роль:", bg='white', font=('Segoe UI', 10)).pack(pady=(10, 5))
        role = ttk.Combobox(dialog, values=['user', 'admin'], state="readonly", width=28)
        role.pack()
        role.set('user')
        
        def save():
            if not username.get() or not password.get():
                messagebox.showerror("Ошибка", "Заполните логин и пароль")
                return
            
            conn = sqlite3.connect('app_management.db')
            cursor = conn.cursor()
            password_hash = hashlib.sha256(password.get().encode()).hexdigest()
            
            try:
                cursor.execute(
                    "INSERT INTO app_users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
                    (username.get(), password_hash, full_name.get(), role.get())
                )
                conn.commit()
                messagebox.showinfo("Успех", "Пользователь добавлен")
                dialog.destroy()
                self.load_users()
            except sqlite3.IntegrityError:
                messagebox.showerror("Ошибка", "Пользователь с таким логином уже существует")
            finally:
                conn.close()
        
        tk.Button(dialog, text="Сохранить", command=save,
                 bg='#28a745', fg='white', font=('Segoe UI', 10, 'bold'),
                 relief='flat', padx=20, pady=5, cursor='hand2').pack(pady=20)
    
    def edit_permissions(self):
        """Редактирование прав доступа к регионам"""
        selected = self.user_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите пользователя")
            return
        
        user_id = self.user_tree.item(selected[0])['values'][0]
        username = self.user_tree.item(selected[0])['values'][1]
        
        perm_window = tk.Toplevel(self.window)
        perm_window.title(f"Права доступа: {username}")
        perm_window.geometry("500x500")
        perm_window.configure(bg='white')
        
        tk.Label(perm_window, text=f"Настройка прав для пользователя {username}",
                font=('Segoe UI', 12, 'bold'), bg='white').pack(pady=10)
        
        # Контейнер с прокруткой
        canvas = tk.Canvas(perm_window, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(perm_window, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='white')
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Загружаем текущие права
        conn = sqlite3.connect('app_management.db')
        cursor = conn.cursor()
        existing_perms = cursor.execute(
            "SELECT region_code, can_view, can_export FROM user_region_access WHERE user_id = ?",
            (user_id,)
        ).fetchall()
        conn.close()
        
        perm_dict = {p[0]: (p[1], p[2]) for p in existing_perms}
        
        # Создаем чекбоксы для каждого региона
        checkboxes = {}
        for code, data in REGIONS_FULL.items():
            frame = tk.Frame(scrollable_frame, bg='white')
            frame.pack(fill=tk.X, pady=3)
            
            tk.Label(frame, text=data['name'], width=30, anchor='w', bg='white').pack(side=tk.LEFT)
            
            view_var = tk.BooleanVar(value=perm_dict.get(code, (True, False))[0])
            export_var = tk.BooleanVar(value=perm_dict.get(code, (True, False))[1])
            
            tk.Checkbutton(frame, text="Просмотр", variable=view_var, bg='white').pack(side=tk.LEFT, padx=5)
            tk.Checkbutton(frame, text="Экспорт", variable=export_var, bg='white').pack(side=tk.LEFT, padx=5)
            
            checkboxes[code] = (view_var, export_var)
        
        def save_permissions():
            conn = sqlite3.connect('app_management.db')
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM user_region_access WHERE user_id = ?", (user_id,))
            
            for code, (view_var, export_var) in checkboxes.items():
                if view_var.get() or export_var.get():
                    cursor.execute(
                        "INSERT INTO user_region_access (user_id, region_code, can_view, can_export) VALUES (?, ?, ?, ?)",
                        (user_id, code, view_var.get(), export_var.get())
                    )
            
            conn.commit()
            conn.close()
            messagebox.showinfo("Успех", "Права сохранены")
            perm_window.destroy()
        
        tk.Button(perm_window, text="Сохранить права", command=save_permissions,
                 bg='#28a745', fg='white', font=('Segoe UI', 10, 'bold'),
                 relief='flat', padx=20, pady=8, cursor='hand2').pack(pady=15)
    
    def delete_user(self):
        """Удаление пользователя"""
        selected = self.user_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите пользователя")
            return
        
        user_id = self.user_tree.item(selected[0])['values'][0]
        username = self.user_tree.item(selected[0])['values'][1]
        
        if username == 'admin':
            messagebox.showerror("Ошибка", "Нельзя удалить администратора")
            return
        
        if messagebox.askyesno("Подтверждение", f"Удалить пользователя '{username}'?"):
            conn = sqlite3.connect('app_management.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM app_users WHERE id = ?", (user_id,))
            cursor.execute("DELETE FROM user_region_access WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            self.load_users()
            messagebox.showinfo("Успех", "Пользователь удален")


class QueryManagementWindow:
    """Окно для управления шаблонами запросов"""
    
    def __init__(self, parent, current_user=None):
        self.window = tk.Toplevel(parent)
        self.window.title("Управление шаблонами запросов")
        self.window.geometry("800x500")
        self.window.configure(bg='white')
        self.current_user = current_user
        
        self.create_widgets()
        self.load_queries()
    
    def create_widgets(self):
        # Список запросов
        self.query_tree = ttk.Treeview(self.window, columns=('ID', 'Название', 'Описание', 'Публичный'), 
                                       show='headings', height=15)
        self.query_tree.heading('ID', text='ID', width=40)
        self.query_tree.heading('Название', text='Название', width=200)
        self.query_tree.heading('Описание', text='Описание', width=350)
        self.query_tree.heading('Публичный', text='Публичный', width=80)
        self.query_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.query_tree.bind('<Double-1>', self.on_query_double_click)
        
        # Кнопки
        btn_frame = tk.Frame(self.window, bg='white')
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="➕ Добавить шаблон", command=self.add_query,
                 bg='#28a745', fg='white', font=('Segoe UI', 10, 'bold'),
                 relief='flat', padx=15, pady=5, cursor='hand2').pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="✏️ Редактировать", command=self.edit_query,
                 bg='#4a86e8', fg='white', font=('Segoe UI', 10, 'bold'),
                 relief='flat', padx=15, pady=5, cursor='hand2').pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="❌ Удалить", command=self.delete_query,
                 bg='#dc3545', fg='white', font=('Segoe UI', 10, 'bold'),
                 relief='flat', padx=15, pady=5, cursor='hand2').pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="Закрыть", command=self.window.destroy,
                 bg='#6c757d', fg='white', font=('Segoe UI', 10, 'bold'),
                 relief='flat', padx=15, pady=5, cursor='hand2').pack(side=tk.LEFT, padx=5)
    
    def load_queries(self):
        """Загрузка списка шаблонов запросов"""
        conn = sqlite3.connect('app_management.db')
        cursor = conn.cursor()
        
        if self.current_user and self.current_user.get('role') == 'admin':
            queries = cursor.execute("SELECT id, name, description, is_public FROM saved_queries").fetchall()
        else:
            queries = cursor.execute(
                "SELECT id, name, description, is_public FROM saved_queries WHERE created_by = ? OR is_public = 1",
                (self.current_user.get('id', 0),)
            ).fetchall()
        
        conn.close()
        
        for item in self.query_tree.get_children():
            self.query_tree.delete(item)
        
        for q in queries:
            public_text = "Да" if q[3] else "Нет"
            self.query_tree.insert('', tk.END, values=(q[0], q[1], q[2], public_text))
    
    def on_query_double_click(self, event):
        self.edit_query()
    
    def add_query(self):
        self.show_query_dialog()
    
    def edit_query(self):
        selected = self.query_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите шаблон")
            return
        self.show_query_dialog(edit_mode=True)
    
    def show_query_dialog(self, edit_mode=False):
        dialog = tk.Toplevel(self.window)
        dialog.title("Редактирование шаблона" if edit_mode else "Новый шаблон")
        dialog.geometry("700x550")
        dialog.configure(bg='white')
        dialog.transient(self.window)
        dialog.grab_set()
        
        query_id = None
        if edit_mode:
            selected = self.query_tree.selection()[0]
            query_id = self.query_tree.item(selected)['values'][0]
            
            conn = sqlite3.connect('app_management.db')
            cursor = conn.cursor()
            q = cursor.execute("SELECT name, description, sql_template, is_public FROM saved_queries WHERE id = ?", (query_id,)).fetchone()
            conn.close()
            
            name_val = q[0]
            desc_val = q[1] if q[1] else ""
            sql_val = q[2]
            public_val = q[3]
        else:
            name_val = ""
            desc_val = ""
            sql_val = ""
            public_val = False
        
        tk.Label(dialog, text="Название:", bg='white', font=('Segoe UI', 10, 'bold')).pack(pady=(15, 5))
        name_entry = tk.Entry(dialog, font=('Segoe UI', 10), width=60)
        name_entry.insert(0, name_val)
        name_entry.pack()
        
        tk.Label(dialog, text="Описание:", bg='white', font=('Segoe UI', 10, 'bold')).pack(pady=(10, 5))
        desc_text = tk.Text(dialog, font=('Segoe UI', 10), height=3, width=60)
        desc_text.insert('1.0', desc_val)
        desc_text.pack()
        
        tk.Label(dialog, text="SQL запрос:", bg='white', font=('Segoe UI', 10, 'bold')).pack(pady=(10, 5))
        sql_text = tk.Text(dialog, font=('Segoe UI', 10), height=12, width=60)
        sql_text.insert('1.0', sql_val)
        sql_text.pack()
        
        public_var = tk.BooleanVar(value=public_val)
        tk.Checkbutton(dialog, text="Публичный шаблон (доступен всем пользователям)", 
                      variable=public_var, bg='white').pack(pady=10)
        
        def save():
            name = name_entry.get().strip()
            description = desc_text.get('1.0', tk.END).strip()
            sql_query = sql_text.get('1.0', tk.END).strip()
            
            if not name or not sql_query:
                messagebox.showerror("Ошибка", "Заполните название и SQL запрос")
                return
            
            conn = sqlite3.connect('app_management.db')
            cursor = conn.cursor()
            
            if edit_mode and query_id:
                cursor.execute("""
                    UPDATE saved_queries 
                    SET name = ?, description = ?, sql_template = ?, is_public = ?
                    WHERE id = ?
                """, (name, description, sql_query, public_var.get(), query_id))
            else:
                cursor.execute("""
                    INSERT INTO saved_queries (name, description, sql_template, is_public, created_by)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, description, sql_query, public_var.get(), self.current_user.get('id') if self.current_user else 1))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Успех", "Шаблон сохранен")
            dialog.destroy()
            self.load_queries()
        
        btn_frame = tk.Frame(dialog, bg='white')
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="Сохранить", command=save,
                 bg='#28a745', fg='white', font=('Segoe UI', 10, 'bold'),
                 relief='flat', padx=20, pady=5, cursor='hand2').pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="Отмена", command=dialog.destroy,
                 bg='#6c757d', fg='white', font=('Segoe UI', 10, 'bold'),
                 relief='flat', padx=20, pady=5, cursor='hand2').pack(side=tk.LEFT, padx=5)
    
    def delete_query(self):
        selected = self.query_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите шаблон")
            return
        
        if messagebox.askyesno("Подтверждение", "Удалить шаблон?"):
            query_id = self.query_tree.item(selected[0])['values'][0]
            
            conn = sqlite3.connect('app_management.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM saved_queries WHERE id = ?", (query_id,))
            conn.commit()
            conn.close()
            
            self.load_queries()
            messagebox.showinfo("Успех", "Шаблон удален")