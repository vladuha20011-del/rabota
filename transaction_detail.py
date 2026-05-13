# transaction_detail.py
# Окно с детальной информацией о транзакции

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
from app_config import BIN_BANKS

class TransactionDetailWindow:
    """Окно с детальной информацией о транзакции"""
    
    def __init__(self, parent, transaction_data, app):
        self.window = tk.Toplevel(parent)
        self.window.title("Информация о поездке")
        self.window.geometry("650x800")
        self.window.configure(bg='white')
        self.window.resizable(False, False)
        
        # Центрируем окно относительно родительского
        self.window.transient(parent)
        self.window.grab_set()
        
        self.transaction = transaction_data
        self.app = app  # Сохраняем ссылку на главное приложение
        
        # Определяем банк по БИНу карты
        self.bank = self.detect_bank()
        
        # Получаем информацию о тарифах для 54 региона по названию маршрута
        self.route_tariffs = None
        route_name = self.transaction.get('Маршрут', '')
        if route_name and route_name != 'Не указано' and route_name != 'None':
            self.route_tariffs = app.get_route_tariffs(route_name)
        
        # Создаем вкладки
        self.create_tabs()
    
    def detect_bank(self):
        """Определение банка по БИНу карты"""
        card_number = self.transaction.get('Номер карты', '')
        if card_number and len(str(card_number)) >= 6:
            bin_number = str(card_number)[:6]
            return BIN_BANKS.get(bin_number, "Неизвестный банк")
        return "Неизвестный банк"
    
    def mask_card_number(self, card_number):
        """Маскировка номера карты (первые 6, потом звездочки, последние 4)"""
        if not card_number or card_number == 'Не указано' or card_number is None:
            return 'Не указано'
        
        card_str = str(card_number).replace(' ', '')
        if len(card_str) >= 10:
            first_six = card_str[:6]
            last_four = card_str[-4:]
            stars = '*' * (len(card_str) - 10)
            return f"{first_six}{stars}{last_four}"
        return card_str
    
    def format_value(self, key, value):
        """Форматирование значения для отображения"""
        if value is None or value == '':
            return "Не указано"
        
        if key == 'Скидка' or key == 'discount':
            try:
                num_value = float(value) if value else 0
                if num_value == 0:
                    return "Не применимо"
                return f"{num_value} ₽"
            except (ValueError, TypeError):
                return str(value)
        
        if key == 'Стоимость проезда' or key == 'price':
            try:
                num_value = float(value) if value else 0
                return f"{num_value} ₽"
            except (ValueError, TypeError):
                return str(value)
        
        return str(value)
    
    def copy_to_clipboard(self, text):
        """Копирование текста в буфер обмена"""
        self.window.clipboard_clear()
        self.window.clipboard_append(text)
        self.show_notification("Скопировано!")
    
    def show_notification(self, message):
        """Показ всплывающего уведомления"""
        notification = tk.Toplevel(self.window)
        notification.overrideredirect(True)
        notification.geometry("150x40")
        notification.configure(bg='#28a745')
        
        x = self.window.winfo_x() + self.window.winfo_width()//2 - 75
        y = self.window.winfo_y() + self.window.winfo_height()//2 - 20
        notification.geometry(f"+{x}+{y}")
        
        label = tk.Label(notification, text=message, fg='white', bg='#28a745',
                        font=('Segoe UI', 11, 'bold'))
        label.pack(expand=True, fill='both')
        
        notification.after(1500, notification.destroy)
    
    def get_check_url(self):
        """Получение URL для проверки билета на основе региона"""
        region_text = self.app.region_var.get()
        if not region_text:
            return "https://qr.sbertroika.ru/cheques"
        
        region_code = region_text.split(' - ')[0]
        
        if region_code == "t2":
            return "https://t2.qr.sbertroika.ru/cheques"
        
        if len(region_code) > 2 and region_code.isdigit():
            base_code = region_code[:2]
        else:
            base_code = region_code
        
        return f"https://{base_code}.qr.sbertroika.ru/cheques"
    
    def export_to_pdf(self):
        """Экспорт информации о поездке в PDF файл"""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            font_paths = [
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/times.ttf",
            ]
            
            font_registered = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('RussianFont', font_path))
                        font_registered = True
                        break
                    except:
                        continue
            
            font_name = 'RussianFont' if font_registered else 'Helvetica'
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            card_number = self.transaction.get('Номер карты', 'unknown')
            if card_number and len(str(card_number)) >= 4:
                card_suffix = str(card_number)[-4:]
            else:
                card_suffix = "0000"
            
            default_filename = f"Поездка_{card_suffix}_{timestamp}.pdf"
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF файлы", "*.pdf"), ("Все файлы", "*.*")],
                initialfile=default_filename
            )
            
            if not file_path:
                return
            
            doc = SimpleDocTemplate(file_path, pagesize=A4,
                                   rightMargin=72, leftMargin=72,
                                   topMargin=72, bottomMargin=72)
            story = []
            
            styles = getSampleStyleSheet()
            
            cell_style = ParagraphStyle(
                'CellStyle',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=10,
                leading=14,
                alignment=0
            )
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontName=font_name,
                fontSize=16,
                spaceAfter=30,
                textColor=colors.HexColor('#333333'),
                alignment=1
            )
            
            title = Paragraph("Информация о поездке", title_style)
            story.append(title)
            story.append(Spacer(1, 20))
            
            card_number = self.transaction.get('Номер карты', 'Не указано')
            masked_card = self.mask_card_number(card_number)
            check_url = self.get_check_url()
            
            def format_datetime(dt_str):
                if not dt_str or dt_str == 'Не указано':
                    return 'Не указано'
                try:
                    str_dt = str(dt_str)
                    if len(str_dt) >= 19:
                        date_part = str_dt[:10]
                        time_part = str_dt[11:19]
                        parts = date_part.split('-')
                        if len(parts) == 3:
                            formatted_date = f"{parts[2]}.{parts[1]}.{parts[0]}"
                            return f"{formatted_date} {time_part}"
                    return str_dt
                except:
                    return str(dt_str)
            
            bank_datetime = format_datetime(self.transaction.get('Дата списания', 'Не указано'))
            trip_datetime = format_datetime(self.transaction.get('Дата регистрации на терминале', 'Не указано'))
            
            data = [
                [Paragraph("<b>Параметр</b>", cell_style), Paragraph("<b>Значение</b>", cell_style)],
                [Paragraph("Номер карты:", cell_style), Paragraph(masked_card, cell_style)],
                [Paragraph("Дата и время списания:", cell_style), Paragraph(bank_datetime, cell_style)],
                [Paragraph("Дата и время поездки:", cell_style), Paragraph(trip_datetime, cell_style)],
                [Paragraph("Серия билета:", cell_style), Paragraph(str(self.transaction.get('Серия билета', 'Не указано')), cell_style)],
                [Paragraph("Номер билета:", cell_style), Paragraph(str(self.transaction.get('Номер билета', 'Не указано')), cell_style)],
                [Paragraph("Гос.номер:", cell_style), Paragraph(str(self.transaction.get('ГРЗ', 'Не указано')), cell_style)],
                [Paragraph("Стоимость проезда:", cell_style), Paragraph(self.format_value('Стоимость проезда', self.transaction.get('Стоимость проезда')), cell_style)],
                [Paragraph("Скидка:", cell_style), Paragraph(self.format_value('Скидка', self.transaction.get('Скидка')), cell_style)],
                [Paragraph("Компания-перевозчик:", cell_style), Paragraph(str(self.transaction.get('Компания', 'Не указано')), cell_style)],
                [Paragraph("<font color='blue'><u>Проверить билет:</u></font>", cell_style), 
                 Paragraph(f"<font color='blue'><u>{check_url}</u></font>", cell_style)],
            ]
            
            table = Table(data, colWidths=[120*mm, 80*mm])
            
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ])
            
            table.setStyle(table_style)
            story.append(table)
            story.append(Spacer(1, 20))
            
            date_style = ParagraphStyle(
                'DateStyle',
                parent=styles['Normal'],
                fontName=font_name,
                alignment=2,
                fontSize=8,
                textColor=colors.grey
            )
            gen_date = Paragraph(f"Отчет сформирован {datetime.now().strftime('%d.%m.%Y в %H:%M')}", date_style)
            story.append(gen_date)
            
            doc.build(story)
            self.show_notification("PDF сохранен!")
            
            open_file = messagebox.askyesno("Экспорт завершен", f"PDF файл успешно сохранен:\n{file_path}\n\nОткрыть файл?")
            if open_file:
                if os.name == 'nt':
                    os.startfile(file_path)
                    
        except ImportError:
            messagebox.showerror("Ошибка", "Для экспорта в PDF требуется установить reportlab")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать PDF: {str(e)}")
    
    def create_tabs(self):
        """Создание вкладок в окне"""
        tab_control = ttk.Notebook(self.window)
        
        main_tab = ttk.Frame(tab_control)
        tab_control.add(main_tab, text="Общая информация")
        
        passenger_tab = ttk.Frame(tab_control)
        tab_control.add(passenger_tab, text="Для пассажиров")
        
        tab_control.pack(expand=1, fill="both", padx=10, pady=10)
        
        self.create_main_tab(main_tab)
        self.create_passenger_tab(passenger_tab)
        
        close_btn = tk.Button(self.window, text="Закрыть", 
                             command=self.window.destroy,
                             bg="#6c757d", fg="white", font=('Segoe UI', 10, 'bold'),
                             relief='flat', padx=20, pady=8, cursor='hand2')
        close_btn.pack(pady=10)
    
    def create_main_tab(self, parent):
        """Создание содержимого основной вкладки"""
        title_label = tk.Label(parent, text="Общая информация о транзакции",
                              font=('Segoe UI', 14, 'bold'), bg='white', fg='#333333')
        title_label.pack(pady=(15, 15))
        
        main_frame = tk.Frame(parent, bg='white', padx=20, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        card_frame = tk.Frame(main_frame, bg='#f8f9fa', relief=tk.SOLID, bd=1)
        card_frame.pack(fill=tk.X, pady=(0, 15))
        
        card_num_frame = tk.Frame(card_frame, bg='#f8f9fa')
        card_num_frame.pack(fill=tk.X, padx=15, pady=(8, 2))
        
        tk.Label(card_num_frame, text="Номер карты:", font=('Segoe UI', 11, 'bold'),
                bg='#f8f9fa', fg='#333333', width=15, anchor='w').pack(side=tk.LEFT)
        
        card_number = self.transaction.get('Номер карты', 'Не указано')
        card_label = tk.Label(card_num_frame, text=str(card_number), font=('Segoe UI', 11, 'bold'),
                             bg='#f8f9fa', fg='#0066cc', anchor='w')
        card_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        copy_card_btn = tk.Button(card_num_frame, text="📋 Копировать", 
                                 command=lambda: self.copy_to_clipboard(str(card_number)),
                                 bg='#28a745', fg='white', font=('Segoe UI', 9, 'bold'),
                                 relief='flat', padx=10, pady=2, cursor='hand2')
        copy_card_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        def on_enter(e):
            copy_card_btn['bg'] = '#218838'
        def on_leave(e):
            copy_card_btn['bg'] = '#28a745'
        copy_card_btn.bind("<Enter>", on_enter)
        copy_card_btn.bind("<Leave>", on_leave)
        
        bank_frame = tk.Frame(card_frame, bg='#f8f9fa')
        bank_frame.pack(fill=tk.X, padx=15, pady=(2, 8))
        
        tk.Label(bank_frame, text="Банк:", font=('Segoe UI', 11, 'bold'),
                bg='#f8f9fa', fg='#333333', width=15, anchor='w').pack(side=tk.LEFT)
        
        tk.Label(bank_frame, text=self.bank, font=('Segoe UI', 11),
                bg='#f8f9fa', fg='#0066cc', anchor='w').pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Frame(main_frame, height=1, bg='#e0e0e0').pack(fill=tk.X, pady=15)
        
        details = [
            ("Дата регистрации", self.transaction.get('Дата регистрации на терминале')),
            ("Дата списания", self.transaction.get('Дата списания')),
            ("Стоимость проезда", self.transaction.get('Стоимость проезда')),
            ("Скидка", self.transaction.get('Скидка')),
            ("ГРЗ", self.transaction.get('ГРЗ')),
            ("Маршрут", self.transaction.get('Маршрут')),
            ("Компания", self.transaction.get('Компания')),
        ]
        
        for label, value in details:
            frame = tk.Frame(main_frame, bg='white')
            frame.pack(fill=tk.X, pady=4)
            tk.Label(frame, text=label + ":", font=('Segoe UI', 10),
                    bg='white', fg='#666666', width=18, anchor='w').pack(side=tk.LEFT)
            formatted_value = self.format_value(label, value)
            value_label = tk.Label(frame, text=formatted_value, font=('Segoe UI', 10, 'bold'),
                                  bg='white', fg='#333333', anchor='w', justify=tk.LEFT,
                                  wraplength=350)
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ticket_frame = tk.Frame(main_frame, bg='#e8f4fd', relief=tk.SOLID, bd=1)
        ticket_frame.pack(fill=tk.X, pady=(15, 0))
        
        ticket_title = tk.Label(ticket_frame, text="Информация о билете", 
                               font=('Segoe UI', 10, 'bold'),
                               bg='#e8f4fd', fg='#0066cc')
        ticket_title.pack(anchor='w', padx=15, pady=(8, 2))
        
        series_value = self.transaction.get('Серия билета', 'Не указано')
        number_value = self.transaction.get('Номер билета', 'Не указано')
        
        copy_btn = tk.Button(ticket_frame, text="📋 Копировать серию и номер", 
                            command=lambda: self.copy_to_clipboard(f"{series_value} {number_value}"),
                            bg='#28a745', fg='white', font=('Segoe UI', 9, 'bold'),
                            relief='flat', padx=10, pady=5, cursor='hand2')
        copy_btn.pack(pady=(0, 10))
    
    def create_passenger_tab(self, parent):
        """Создание содержимого вкладки для пассажиров"""
        title_label = tk.Label(parent, text="Информация для пассажиров",
                              font=('Segoe UI', 14, 'bold'), bg='white', fg='#333333')
        title_label.pack(pady=(15, 15))
        
        main_frame = tk.Frame(parent, bg='white', padx=20, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        card_number = self.transaction.get('Номер карты', 'Не указано')
        masked_card = self.mask_card_number(card_number)
        
        def format_datetime(dt_str):
            if not dt_str or dt_str == 'Не указано':
                return 'Не указано'
            try:
                str_dt = str(dt_str)
                if len(str_dt) >= 19:
                    date_part = str_dt[:10]
                    time_part = str_dt[11:19]
                    parts = date_part.split('-')
                    if len(parts) == 3:
                        formatted_date = f"{parts[2]}.{parts[1]}.{parts[0]}"
                        return f"{formatted_date} {time_part}"
                return str_dt
            except:
                return str(dt_str)
        
        bank_datetime = format_datetime(self.transaction.get('Дата списания', 'Не указано'))
        trip_datetime = format_datetime(self.transaction.get('Дата регистрации на терминале', 'Не указано'))
        
        passenger_info = [
            ("Номер карты:", masked_card),
            ("Дата и время списания:", bank_datetime),
            ("Дата и время поездки:", trip_datetime),
            ("Серия билета:", self.transaction.get('Серия билета', 'Не указано')),
            ("Номер билета:", self.transaction.get('Номер билета', 'Не указано')),
            ("Гос.номер:", self.transaction.get('ГРЗ', 'Не указано')),
            ("Стоимость проезда:", self.format_value('Стоимость проезда', self.transaction.get('Стоимость проезда'))),
            ("Скидка:", self.format_value('Скидка', self.transaction.get('Скидка'))),
            ("Компания-перевозчик:", self.transaction.get('Компания', 'Не указано')),
        ]
        
        info_frame = tk.Frame(main_frame, bg='#f8f9fa', relief=tk.SOLID, bd=1)
        info_frame.pack(fill=tk.X, pady=5)
        
        info_title = tk.Label(info_frame, text="Детали поездки", 
                             font=('Segoe UI', 12, 'bold'), 
                             bg='#f8f9fa', fg='#333333')
        info_title.pack(pady=(10, 5))
        
        tk.Frame(info_frame, height=1, bg='#e0e0e0').pack(fill=tk.X, padx=10, pady=5)
        
        content_frame = tk.Frame(info_frame, bg='#f8f9fa', padx=20, pady=10)
        content_frame.pack(fill=tk.X)
        
        for i, (label, value) in enumerate(passenger_info):
            row_frame = tk.Frame(content_frame, bg='#f8f9fa')
            row_frame.pack(fill=tk.X, pady=3)
            tk.Label(row_frame, text=label, font=('Segoe UI', 10, 'bold'),
                    bg='#f8f9fa', fg='#333333', width=22, anchor='w').pack(side=tk.LEFT)
            color = '#0066cc' if i == 0 else '#333333'
            tk.Label(row_frame, text=value, font=('Segoe UI', 10, 'bold' if i == 0 else ''),
                    bg='#f8f9fa', fg=color, anchor='w', wraplength=300).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        button_frame = tk.Frame(main_frame, bg='white')
        button_frame.pack(pady=15)
        
        export_pdf_btn = tk.Button(button_frame, text="📄 Экспорт в PDF", 
                                  command=self.export_to_pdf,
                                  bg='#dc3545', fg='white', font=('Segoe UI', 10, 'bold'),
                                  relief='flat', padx=20, pady=8, cursor='hand2')
        export_pdf_btn.pack()