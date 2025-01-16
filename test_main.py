"""
Модуль для тестирования класса SystemMonitorApp.

Содержит автотесты проверящие штатную отработку всего функционала класса
"""
import pytest
from unittest.mock import MagicMock, patch
import sqlite3
import tkinter as tk
from main import SystemMonitorApp


@pytest.fixture(scope='function')
def app():
    """Фикстура отвечающая за инициализацию приложения для каждого теста."""
    frame = tk.Tk()
    app = SystemMonitorApp(frame)
    yield app
    try:
        frame.destroy()
    except tk.TclError:
        pass


def test_start_recording(app):
    """
    Проверяет что при нажатии на кнопку 'начать запись' флаг recording = True.

    Также проверяет сокрытие всех кнопок кроме 'остановить'

    и тестирует срабатываение функций 'update_timer' и 'update_disk_usage'
    """
    app.update_timer = MagicMock()
    app.update_disk_usage = MagicMock()
    app.start_button.pack_forget = MagicMock()
    app.stop_button.pack = MagicMock()
    app.timer_label.pack = MagicMock()

    app.start_recording()
    assert app.recording is True
    app.start_button.pack_forget.assert_called_once()
    app.stop_button.pack.assert_called_once()
    app.timer_label.pack.assert_called_once()
    app.update_timer.assert_called_once()
    app.update_disk_usage.assert_called_once()


def test_setup_db(app):
    """Проверяет соединение с базой данных."""
    app.setup_db()
    assert isinstance(app.conn, sqlite3.Connection)
    assert isinstance(app.c, sqlite3.Cursor)


def test_save_to_db(app):
    """Проверяет корректность сохранения данных в бд."""
    mock_conn = MagicMock()
    app.conn = mock_conn
    mock_cursor = MagicMock()
    app.c = mock_cursor

    app.save_to_db(10.5, (1024, 2048), (512, 1024))

    mock_cursor.execute.assert_called_once_with(
        '''INSERT INTO records (cpu, osu_free, osu_total, disk_free, disk_total) VALUES (?, ?, ?, ?, ?)''',
        (10.5, 1024, 2048, 512, 1024)
    )
    mock_conn.commit.assert_called_once()
    mock_cursor.execute('''SELECT cpu, osu_free, osu_total, disk_free, disk_total FROM records''')
    records = mock_cursor.fetchall()
    for record in records:
        assert record == (10.5, 1024, 2048, 512, 1024)


def test_get_cpu_usage(app):
    """Проверяет корректность возвращаемых показателей ЦПУ."""
    with patch('psutil.cpu_percent', return_value=25.0):
        assert app.get_cpu_usage() == 25.0


def test_get_osu_usage(app):
    """Проверяет корректность возвращаемых показателей ОЗУ."""
    mock_memory = MagicMock()
    mock_memory.available = 1024 * 1024
    mock_memory.total = 2048 * 1024
    with patch('psutil.virtual_memory', return_value=mock_memory):
        assert app.get_osu_usage() == (1024, 2048)


def test_get_disk_usage(app):
    """Проверяет корректность возвращаемых показателей ПЗУ."""
    mock_partition = MagicMock()
    mock_partition.mountpoint = '/'
    mock_usage = MagicMock()
    mock_usage.total = 1024 * 1024
    mock_usage.free = 512 * 1024
    with patch('psutil.disk_partitions', return_value=[mock_partition]):
        with patch('psutil.disk_usage', return_value=mock_usage):
            assert app.get_disk_usage() == (512, 1024)


def test_stop_recording(app):
    """
    Проверяет что при нажатии на кнопку 'остановить' флаг recording = False.

    Также проверяет появление всех кнопок кроме 'остановить'
    """
    app.start_button.pack = MagicMock()
    app.history_button.pack = MagicMock()
    app.change_tick_button.pack = MagicMock()
    app.stop_button.pack_forget = MagicMock()
    app.timer_label.pack_forget = MagicMock()

    app.stop_recording()
    assert app.recording is False
    app.stop_button.pack_forget.assert_called_once()
    app.timer_label.pack_forget.assert_called_once()
    app.start_button.pack.assert_called_once()
    app.history_button.pack.assert_called_once()
    app.change_tick_button.pack.assert_called_once()


def test_update_timer(app, capsys):
    """Проверяет корректность работы таймера."""
    app.timer_label.config = MagicMock()
    app.recording = True
    app.update_timer()
    assert app.elapsed_time == 1
    app.timer_label.config.assert_called_once_with(text='00:01')


def test_update_disk_usage(app):
    """
    Проверяет корректность вывода информации о ЦПУ, ОЗУ, ПЗУ на экран.

    Также проверяет корректность записи данных в бд
    """
    app.get_cpu_usage = MagicMock(return_value=10.5)
    app.get_osu_usage = MagicMock(return_value=(1024, 2048))
    app.get_disk_usage = MagicMock(return_value=(512, 1024))
    app.save_to_db = MagicMock()

    app.table_tree = MagicMock()
    app.table_tree.get_children.return_value = []

    app.recording = True

    app.update_disk_usage()

    app.table_tree.insert.assert_any_call('', 'end', values=('ЦПУ', 10.5, '-'))
    app.table_tree.insert.assert_any_call('', 'end', values=('ОЗУ', 1024, 2048))
    app.table_tree.insert.assert_any_call('', 'end', values=('ПЗУ', 512, 1024))

    app.save_to_db.assert_called_once_with(10.5, (1024, 2048), (512, 1024))


def test_show_history(app):
    """Проверяет корректность отображения данных в окне истории."""
    mock_record = (10.5, 1024, 2048, 512, 1024)
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [mock_record]
    app.c = mock_cursor

    with patch('tkinter.ttk.Treeview') as mock_treeview:
        mock_history_tree = MagicMock()
        mock_treeview.return_value = mock_history_tree

        app.show_history()

        mock_history_tree.insert.assert_called_once_with('', 'end', values=mock_record)


def test_change_tick(app):
    """Провряет корректность работы окна изменения тика."""
    with patch('tkinter.simpledialog.askinteger', return_value=500):
        app.change_tick()
        assert app.tick_interval == 500


def test_on_closing(app):
    """Проверяет корректность закрытия соединения с бд."""
    mock_conn = MagicMock()
    app.conn = mock_conn

    app.on_closing()

    mock_conn.close.assert_called_once()
