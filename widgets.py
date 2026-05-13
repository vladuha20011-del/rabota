# widgets.py
# Содержит пользовательские виджеты: ModernButton, ProgressBar, DatePicker

import tkinter as tk
from tkinter import ttk
from datetime import datetime

class ProgressBar(tk.Frame):
    """Прогресс-бар с анимацией"""
    
    def __init__(self, parent, width=400, height=20):
        super().__init__(parent, height=height)
        self.width = width
        self.height = height
        
        # Основной холст
        self.canvas = tk.Canvas(self, width=width, height=height, 
                               bg='white', highlightthickness=1,
                               highlightbackground='#cccccc')
        self.canvas.pack()
        
        # Переменные для анимации
        self.progress = 0
        self.is_running = False
        self.animation_id = None
        
    def start(self):
        """Запуск анимации прогресс-бара"""
        self.is_running = True
        self.progress = 0
        self.animate()
    
    def animate(self):
        """Анимация заполнения прогресс-бара"""
        if not self.is_running:
            return
        
        # Увеличиваем прогресс
        self.progress = min(self.progress + 2, 100)
        
        # Очищаем canvas
        self.canvas.delete("all")
        
        # Рисуем фон
        self.canvas.create_rectangle(0, 0, self.width, self.height, 
                                    fill='white', outline='')
        
        # Рисуем прогресс
        progress_width = (self.width * self.progress) / 100
        self.canvas.create_rectangle(0, 0, progress_width, self.height,
                                    fill='#4CAF50', outline='')
        
        # Рисуем рамку
        self.canvas.create_rectangle(0, 0, self.width, self.height,
                                    outline='#cccccc')
        
        # Добавляем текст прогресса
        self.canvas.create_text(self.width/2, self.height/2,
                               text=f"{self.progress}%",
                               fill='#333333',
                               font=('Arial', 9))
        
        # Продолжаем анимацию если не достигли 100%
        if self.progress < 100:
            self.animation_id = self.after(50, self.animate)
        else:
            self.is_running = False
    
    def stop(self):
        """Остановка анимации"""
        self.is_running = False
        if self.animation_id:
            self.after_cancel(self.animation_id)
        self.canvas.delete("all")
        
        # Рисуем пустой прогресс-бар
        self.canvas.create_rectangle(0, 0, self.width, self.height,
                                    fill='white', outline='#cccccc')
        
    def set_progress(self, value):
        """Установка конкретного значения прогресса"""
        self.progress = max(0, min(100, value))
        self.canvas.delete("all")
        
        # Рисуем фон
        self.canvas.create_rectangle(0, 0, self.width, self.height, 
                                    fill='white', outline='')
        
        # Рисуем прогресс
        progress_width = (self.width * self.progress) / 100
        self.canvas.create_rectangle(0, 0, progress_width, self.height,
                                    fill='#4CAF50', outline='')
        
        # Рисуем рамку
        self.canvas.create_rectangle(0, 0, self.width, self.height,
                                    outline='#cccccc')
        
        # Добавляем текст прогресса
        self.canvas.create_text(self.width/2, self.height/2,
                               text=f"{self.progress}%",
                               fill='#333333',
                               font=('Arial', 9))


class ModernButton(tk.Canvas):
    """Современная кнопка с эффектами"""
    
    def __init__(self, parent, text, command=None, width=120, height=38, 
                 bg_color="#4a86e8", hover_color="#3a76d8", text_color="white", 
                 disabled_color="#cccccc", disabled_text_color="#888888",
                 corner_radius=8, font=('Segoe UI', 10, 'bold'),
                 state='normal'):
        super().__init__(parent, width=width, height=height, 
                        bg='white', highlightthickness=0)
        
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.disabled_color = disabled_color
        self.text_color = text_color
        self.disabled_text_color = disabled_text_color
        self.corner_radius = corner_radius
        self.font = font
        self.text = text
        self.is_hovered = False
        self._state = state
        
        self.update_bindings()
        self.draw_button()
    
    def update_bindings(self):
        """Обновление привязок событий"""
        self.unbind("<Button-1>")
        self.unbind("<Enter>")
        self.unbind("<Leave>")
        
        if self._state == 'normal':
            self.bind("<Button-1>", self.on_click)
            self.bind("<Enter>", self.on_enter)
            self.bind("<Leave>", self.on_leave)
    
    def draw_button(self):
        """Отрисовка кнопки"""
        self.delete("all")
        
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        
        if self._state == 'disabled':
            fill_color = self.disabled_color
            text_color = self.disabled_text_color
        elif self.is_hovered:
            fill_color = self.hover_color
            text_color = self.text_color
        else:
            fill_color = self.bg_color
            text_color = self.text_color
        
        self.create_rounded_rect(0, 0, width, height, self.corner_radius, 
                                 fill=fill_color, outline=fill_color)
        
        self.create_text(width//2, height//2, text=self.text, 
                        fill=text_color, font=self.font)
    
    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Создание прямоугольника с закругленными углами"""
        points = []
        points.extend([x1 + radius, y1])
        points.extend([x2 - radius, y1])
        points.extend([x2, y1 + radius])
        points.extend([x2, y2 - radius])
        points.extend([x2 - radius, y2])
        points.extend([x1 + radius, y2])
        points.extend([x1, y2 - radius])
        points.extend([x1, y1 + radius])
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def on_enter(self, event):
        if self._state == 'normal':
            self.is_hovered = True
            self.draw_button()
    
    def on_leave(self, event):
        if self._state == 'normal':
            self.is_hovered = False
            self.draw_button()
    
    def on_click(self, event):
        if self._state == 'normal' and self.command:
            self.command()
    
    def config(self, **kwargs):
        if 'state' in kwargs:
            self._state = kwargs['state']
            self.is_hovered = False
            self.update_bindings()
            self.draw_button()
        if 'text' in kwargs:
            self.text = kwargs['text']
            self.draw_button()
        if 'command' in kwargs:
            self.command = kwargs['command']
    
    @property
    def state(self):
        return self._state
    
    @state.setter
    def state(self, value):
        self.config(state=value)


class DatePicker:
    """Пользовательский виджет для выбора даты"""
    
    def __init__(self, parent, default_date=None):
        self.frame = ttk.Frame(parent)
        
        if default_date is None:
            default_date = datetime.now()
        
        self.current_date = default_date
        
        self.year_var = tk.StringVar(value=str(default_date.year))
        self.month_var = tk.StringVar(value=f"{default_date.month:02d}")
        self.day_var = tk.StringVar(value=f"{default_date.day:02d}")
        
        ttk.Label(self.frame, text="Год:", font=('Segoe UI', 9)).grid(row=0, column=0, padx=(0, 2))
        year_entry = ttk.Entry(self.frame, textvariable=self.year_var, width=6, font=('Segoe UI', 9))
        year_entry.grid(row=0, column=1, padx=(0, 5))
        
        ttk.Label(self.frame, text="Месяц:", font=('Segoe UI', 9)).grid(row=0, column=2, padx=(5, 2))
        self.month_combo = ttk.Combobox(self.frame, textvariable=self.month_var, 
                                       values=[f"{i:02d}" for i in range(1, 13)], 
                                       width=3, state="readonly", font=('Segoe UI', 9))
        self.month_combo.grid(row=0, column=3, padx=(0, 5))
        
        ttk.Label(self.frame, text="День:", font=('Segoe UI', 9)).grid(row=0, column=4, padx=(5, 2))
        self.day_combo = ttk.Combobox(self.frame, textvariable=self.day_var, 
                                     width=3, state="readonly", font=('Segoe UI', 9))
        self.day_combo.grid(row=0, column=5)
        
        self.month_combo.bind('<<ComboboxSelected>>', self.update_days)
        self.year_var.trace('w', lambda *args: self.update_days())
        
        self.update_days()
    
    def grid(self, **kwargs):
        return self.frame.grid(**kwargs)
    
    def pack(self, **kwargs):
        return self.frame.pack(**kwargs)
    
    def get_date(self):
        try:
            year = int(self.year_var.get())
            month = int(self.month_var.get())
            day = int(self.day_var.get())
            datetime(year, month, day)
            return datetime(year, month, day)
        except (ValueError, TypeError):
            return datetime.now()
    
    def set_date(self, date):
        self.year_var.set(str(date.year))
        self.month_var.set(f"{date.month:02d}")
        self.day_var.set(f"{date.day:02d}")
        self.update_days()
    
    def update_days(self, event=None):
        try:
            year = int(self.year_var.get())
            month = int(self.month_var.get())
            
            if month in [1, 3, 5, 7, 8, 10, 12]:
                days_in_month = 31
            elif month in [4, 6, 9, 11]:
                days_in_month = 30
            else:
                if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                    days_in_month = 29
                else:
                    days_in_month = 28
            
            days = [f"{i:02d}" for i in range(1, days_in_month + 1)]
            self.day_combo['values'] = days
            
            current_day = int(self.day_var.get())
            if current_day > days_in_month:
                self.day_var.set(f"{days_in_month:02d}")
            elif current_day < 1:
                self.day_var.set("01")
        except (ValueError, TypeError):
            days = [f"{i:02d}" for i in range(1, 32)]
            self.day_combo['values'] = days