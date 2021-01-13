import sys
import os
import configparser
import requests

import PySide2
from PySide2 import QtCore
from PySide2.QtWidgets import QApplication, QMainWindow
from PySide2.QtCore import QTimer
from PySide2.QtGui import QStandardItemModel, QStandardItem

from window import Ui_MainWindow
from dataclasses import dataclass
import win32process
import win32api
import win32con


@dataclass
class ProcInfo:
    pid = None
    start_time = None
    name = ""

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_lists)
        self.update_timer.start(1000)

        self.ui.pushButton.clicked.connect(self.on_notification_click)

        self.proc_list_model = QStandardItemModel(self.ui.listView)
        self.ui.listView.setModel(self.proc_list_model)

        config = configparser.ConfigParser()
        config.read('config.ini')
        self.bot_token = config['main']['bot_token']
        self.user_id = config['main']['user_id']
        
        self.watched_procs = []
        
        self.proc_infos = {}
        
    def on_notification_click(self):
        idx = self.ui.listView.selectedIndexes()[0]
        item = self.proc_list_model.itemFromIndex(idx)
        proc = item.data()
        self.watched_procs.append(proc)

    def update_lists(self):
        self.update_process_list()
        self.update_watched_procs()
        
    def update_process_list(self):
        pids = win32process.EnumProcesses()
        updated_proc_infos = {}
        for pid in pids:
            if pid in self.proc_infos:
                updated_proc_infos[pid] = self.proc_infos[pid]
                continue

            try:
                handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, 0, pid)
                name = win32process.GetModuleFileNameEx(handle, 0)
                _, name = os.path.split(name)
                times = win32process.GetProcessTimes(handle)
                
                proc_info = ProcInfo()
                proc_info.name = name
                proc_info.start_time = times['CreationTime']
                proc_info.pid = pid
                updated_proc_infos[pid] = proc_info

            except Exception as e:
                print(str(e))
                updated_proc_infos[pid] = None

        new_procs = [proc for (pid, proc) in updated_proc_infos.items() if proc is not None and pid not in self.proc_infos]
        self.proc_infos = updated_proc_infos

        for row in reversed(range(0, self.proc_list_model.rowCount())):
            item = self.proc_list_model.item(row)
            proc = item.data()
            if proc.pid not in self.proc_infos:
                self.proc_list_model.removeRow(row)

        new_procs = sorted(new_procs, key=lambda proc: proc.start_time)
        for proc in new_procs:
            item = QStandardItem(proc.name)
            item.setData(proc)
            self.proc_list_model.insertRow(0, item)
            
    def update_watched_procs(self):
        killed_procs = [proc for proc in self.watched_procs if proc.pid not in self.proc_infos]
        for proc in killed_procs:
            self.send_message_to_bot("process {} is killed".format(proc.name))

        self.watched_procs = [proc for proc in self.watched_procs if proc not in killed_procs]
            
    def send_message_to_bot(self, text):
        message = 'https://api.telegram.org/bot' + self.bot_token + '/sendMessage?chat_id=' + self.user_id +'&text=' + text 
        response = requests.get(message)
        print(response.json())
        

if __name__ == "__main__":
    PySide2.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
