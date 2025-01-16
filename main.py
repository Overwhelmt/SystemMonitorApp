"""Модуль отвечающий за создание приложения отслеживающего показатели ПК."""
import tkinter as tk
from tkinter import simpledialog, ttk
import sqlite3
import psutil


class SystemMonitorApp:
    """
    Класс представляющий отрисовку и работу приложения мониторинга ПК.

    Атрибуты:
        frame(tk.TK): Основной экран
        table_tree(TreeView): Табличное отображение данных
        tick_interval(int): Интервал обновления данных
        recording(bool): Активна ли запись данных в бд

    Метода:
        setup_ui(): Активирует интерфейс
        setup_ui(): Соединяется с базой данных
    """

    def __init__(self, frame):
        """Конструктор класса."""
        self.frame = frame
        self.frame.title('Состояние Системы')
        self.table_tree = ttk.Treeview(self.frame,
                                       columns=('Device', 'Free', 'Total'),
                                       show='headings')
        self.tick_interval = 1000
        self.elapsed_time = 0
        self.recording = False
        self.setup_ui()
        self.setup_db()

    def setup_ui(self):
        """Отрисовывает UI главного экрана."""
        self.table_tree.heading('Device', text='Устройство')
        self.table_tree.heading('Free', text='Свободно')
        self.table_tree.heading('Total', text='Всего')
        self.table_tree.pack(expand=True, fill=tk.BOTH)

        self.start_button = tk.Button(self.frame, text='Начать запись',
                                      padx=10, pady=10,
                                      command=self.start_recording)
        self.history_button = tk.Button(self.frame, text='История',
                                        padx=10, pady=10,
                                        command=self.show_history)
        self.change_tick_button = tk.Button(self.frame,
                                            text='Изменить время тика',
                                            padx=10, pady=10,
                                            command=self.change_tick)
        self.stop_button = tk.Button(self.frame, text='Остановить',
                                     padx=10, pady=10,
                                     command=self.stop_recording)

        self.start_button.pack(side=tk.LEFT, padx=5)
        self.history_button.pack(side=tk.LEFT, padx=5)
        self.change_tick_button.pack(side=tk.LEFT, padx=5)
        self.stop_button.pack_forget()

        self.timer_label = tk.Label(self.frame, text='00:00')
        self.timer_label.pack_forget()

    def setup_db(self):
        """Соединяется с бд и создает таблицу records для записи данных."""
        self.conn = sqlite3.connect('system_data.db')
        self.c = self.conn.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS records (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  cpu REAL,
                  osu_free REAL,
                  osu_total REAL,
                  disk_free REAL,
                  disk_total REAL)''')
        self.conn.commit()

    def save_to_db(self, cpu_info, osu_info, disk_info):
        """Сохраняет полученные значения ЦПУ, ОЗУ, ПЗУ в бд."""
        self.c.execute(
            '''INSERT INTO records (cpu, osu_free, osu_total, disk_free, disk_total) VALUES (?, ?, ?, ?, ?)''',
            (cpu_info, osu_info[0], osu_info[1], disk_info[0], disk_info[1]))
        self.conn.commit()

    def start_recording(self):
        """
        Команда для начала работы программы и записи данных в бд.

        Запускает секундомер и метод обновляющий данные на экране
        """
        self.recording = True
        self.start_button.pack_forget()
        self.history_button.pack_forget()
        self.change_tick_button.pack_forget()
        self.stop_button.pack(side=tk.LEFT, padx=5)
        self.timer_label.pack(side=tk.LEFT, padx=5)
        self.update_timer()
        self.update_disk_usage()

    def stop_recording(self):
        """Остановливает работу программы и запись в бд."""
        self.recording = False
        self.stop_button.pack_forget()
        self.timer_label.pack_forget()
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.history_button.pack(side=tk.LEFT, padx=5)
        self.change_tick_button.pack(side=tk.LEFT, padx=5)
        self.elapsed_time = 0

    def update_timer(self):
        """Секундомер."""
        if self.recording:
            self.elapsed_time += 1
            self.minutes, self.seconds = divmod(self.elapsed_time, 60)
            self.timer_label.config(
                text='{:02}:{:02}'.format(int(self.minutes), int(self.seconds)))
            self.frame.after(1000, self.update_timer)

    @staticmethod
    def get_cpu_usage():
        """Получает данные ЦПУ в %."""
        return psutil.cpu_percent()

    @staticmethod
    def get_osu_usage():
        """Получает данные ОЗУ в КБ."""
        osu_available = psutil.virtual_memory().available // 1024
        osu_total = psutil.virtual_memory().total // 1024
        return osu_available, osu_total

    @staticmethod
    def get_disk_usage():
        """Получает данные ПЗУ в КБ."""
        partitions = psutil.disk_partitions()
        disk_info_total = 0
        disk_info_free = 0

        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info_total += usage.total
                disk_info_free += usage.free
            except PermissionError:
                continue
        return disk_info_free // 1024, disk_info_total // 1024

    def update_disk_usage(self):
        """Обновляет данные на экране и сохраняет изменения в бд."""
        if not self.recording:
            return

        for i in self.table_tree.get_children():
            self.table_tree.delete(i)

        self.cpu_info = self.get_cpu_usage()
        self.osu_info = self.get_osu_usage()
        self.disk_info = self.get_disk_usage()

        self.table_tree.insert('', 'end', values=('ЦПУ', self.cpu_info, '-'))
        free, total = self.osu_info
        self.table_tree.insert('', 'end', values=('ОЗУ', free, total))
        free, total = self.disk_info
        self.table_tree.insert('', 'end', values=('ПЗУ', free, total))

        self.save_to_db(self.cpu_info, self.osu_info, self.disk_info)

        self.frame.after(self.tick_interval, self.update_disk_usage)

    def show_history(self):
        """Выводит информацию о записанных данных на экран."""
        self.c.execute('''
              SELECT cpu, osu_free, osu_total, disk_free, disk_total
              FROM records
              ''')
        self.records = self.c.fetchall()

        self.history_window = tk.Toplevel(self.frame)
        self.history_window.title('История')

        self.history_tree = ttk.Treeview(self.history_window,
                                         columns=('ЦПУ',
                                                  'ОЗУ свободно',
                                                  'ОЗУ всего',
                                                  'ПЗУ свободно',
                                                  'ПЗУ всего'),
                                         show='headings')
        self.history_tree.heading('ЦПУ', text='ЦПУ(%)')
        self.history_tree.heading('ОЗУ свободно', text='ОЗУ свободно(КБ)')
        self.history_tree.heading('ОЗУ всего', text='ОЗУ всего(КБ)')
        self.history_tree.heading('ПЗУ свободно', text='ПЗУ свободно(КБ)')
        self.history_tree.heading('ПЗУ всего', text='ПЗУ всего(КБ)')
        self.history_tree.pack(expand=True, fill=tk.BOTH)

        for self.record in self.records:
            self.history_tree.insert('', 'end', values=self.record)

    def change_tick(self):
        """Изменяет время тика обновления данных."""
        new_tick = simpledialog.askinteger('Изменить время тика',
                                           'Введите новое время тика (мс):',
                                           minvalue=1, maxvalue=1000)
        if new_tick:
            self.tick_interval = new_tick

    def on_closing(self):
        """Закрывает соединение с бд и закрывает программу."""
        self.conn.close()
        self.frame.destroy()


if __name__ == '__main__':
    frame = tk.Tk()
    app = SystemMonitorApp(frame)
    app.setup_db()
    frame.protocol('WM_DELETE_WINDOW', app.on_closing)
    frame.mainloop()
