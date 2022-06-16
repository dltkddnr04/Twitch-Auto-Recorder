import requests
import json
import subprocess
import time
import sys
import threading
import pickle
import os
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QTextBrowser, QGridLayout, QGroupBox, QLabel, QMessageBox)
import PyQt5.QtWidgets as qtwid
from PyQt5.QtCore import Qt

client_id = "5ayor8kn22hxinl6way2j1ejzi41g2"
client_secret = "8tp18ssnpzbrzyyf0he83q3lsfayyx"

req = requests.post("https://id.twitch.tv/oauth2/token?client_id=" + client_id + "&client_secret=" + client_secret + "&grant_type=client_credentials")
json_data = json.loads(req.text)
access_token = json_data["access_token"]

# streamer_list.pikle 파일이 없으면 생성
if not os.path.isfile("streamer_list.pickle"):
    with open("streamer_list.pickle", "wb") as f:
        pickle.dump([], f)

class MyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        grid = QGridLayout()
        grid.addWidget(self.createSetupGroup(), 0, 0)
        grid.addWidget(self.createTerminalGroup(), 1, 0)

        self.setLayout(grid)

        self.setWindowTitle('트위치 자동 박제기')
        self.resize(600, 400)
        self.show()

        self.start_program()

        now_version = "1.0.0"
        req = requests.get("https://api.github.com/repos/dltkddnr04/Twitch-Auto-Recorder/releases/latest")
        last_version = req.json()["name"]

        now_version = now_version.split('.')
        last_version = last_version[1:].split('.')

        if int(now_version[0]) != int(last_version[0]):
            QMessageBox.information(self, "Error", "새로운 버전이 사용가능합니다.\n업데이트해주세요.\n업데이트 주소:\nhttps://github.com/dltkddnr04/Twitch-Auto-Recorder/releases")
            sys.exit()
        else:
            if int(now_version[1]) != int(last_version[1]):
                QMessageBox.information(self, "Error", "새로운 버전이 사용가능합니다.\n업데이트해주세요.\n업데이트 주소:\nhttps://github.com/dltkddnr04/Twitch-Auto-Recorder/releases")
                sys.exit()
            else:
                if int(now_version[2]) != int(last_version[2]):
                    QMessageBox.information(self, "Error", "새로운 버전이 사용가능합니다.\n업데이트해주세요.\n업데이트 주소:\nhttps://github.com/dltkddnr04/Twitch-Auto-Recorder/releases")
                    sys.exit()

    def createSetupGroup(self):
        groupbox = QGroupBox('설정')
        grid = QGridLayout()

        self.streamer_edit = qtwid.QLineEdit(self)
        self.save_btn = qtwid.QPushButton("추가",self)
        self.lbox_item = qtwid.QListWidget(self)
        #self.btn_group = qtwid.QPushButton("등록해제",self)

        self.streamer_edit.setToolTip('스트리머의 영문 닉네임을 입력하세요')
        
        grid.addWidget(QLabel("스트리머 영문 닉네임"), 0, 0)
        grid.addWidget(self.streamer_edit, 1, 0)
        grid.addWidget(self.save_btn, 1, 1)
        grid.addWidget(self.lbox_item, 2, 0)
        grid.addWidget(self.btn_group(), 2, 1)

        self.save_btn.clicked.connect(self.Btn_addClick)        
        self.lbox_item.itemSelectionChanged.connect(self.Lbox_itemSelectionChange)

        groupbox.setLayout(grid)
        return groupbox

    def btn_group(self):
        groupbox = QGroupBox()
        grid = QGridLayout()

        self.btn_remove = qtwid.QPushButton("등록해제",self)
        #self.btn_start = qtwid.QPushButton("시작",self)
        #self.btn_stop = qtwid.QPushButton("정지",self)

        grid.addWidget(self.btn_remove, 0, 0)
        #grid.addWidget(self.btn_start, 1, 0)
        #grid.addWidget(self.btn_stop, 2, 0)

        self.btn_remove.clicked.connect(self.Btn_removeClick)
        #self.btn_start.clicked.connect(self.Btn_startClick)
        #self.btn_stop.clicked.connect(self.Btn_stopClick)

        self.btn_remove.setEnabled(False)
        #self.btn_stop.setEnabled(False)

        groupbox.setLayout(grid)
        return groupbox

    def createTerminalGroup(self):
        groupbox = QGroupBox('로그')
        grid = QGridLayout()

        self.tb = QTextBrowser()
        grid.addWidget(self.tb, 0, 0)

        groupbox.setLayout(grid)

        return groupbox

    def console_print(self, message):
        date = "[" + datetime.today().strftime('%Y-%m-%d %H:%M:%S') + "]"
        self.tb.append(date + " " + message)

    def stream_check(self, streamer_id):
        headers = {'Client-ID': client_id, 'Authorization': 'Bearer ' + access_token}
        req = requests.get("https://api.twitch.tv/helix/streams?user_id=" + streamer_id, headers=headers)
    
        json_data = json.loads(req.text)
        stream_status = json_data["data"]

        if not stream_status:
            return False
        else:
            return True

    def stream_download(self, streamer):
        date = datetime.today().strftime('%Y-%m-%d %H-%M-%S')
        path = "./" + streamer + "/" + date + ".ts"
    
        subprocess.run(["streamlink", "twitch.tv/" + streamer, "best", "-o", path])

    def stream_record(self, streamer, streamer_id):
        while True:
            if self.stream_check(streamer_id):
                self.console_print(streamer + "님 방송 시작")
                self.stream_download(streamer)
                self.console_print(streamer + "님 방송 종료")
            if not self.lbox_item.findItems(streamer, Qt.MatchExactly):
                break
            time.sleep(3)

    def start_program(self):
        self.console_print("프로그램 시작")

        with open("streamer_list.pickle", 'rb') as f:
            streamer_list = pickle.load(f)
            if streamer_list != []:
                self.console_print("스트리머 불러오기 완료")

                for streamer in streamer_list:
                    self.lbox_item.addItem(streamer)
                    req = requests.get("https://api.twitch.tv/helix/users?login=" + streamer, headers={"Client-ID": client_id, "Authorization": "Bearer " + access_token})

                    json_data = json.loads(req.text)
                    streamer_id = json_data["data"][0]["id"]

                    threading.Thread(target=self.stream_record, args=(streamer, streamer_id), name=streamer_id).start()

    def Btn_addClick(self):
        self.streamer = self.streamer_edit.text()
        if self.streamer == "":
            QMessageBox.information(self, "Error", "스트리머 이름이 비어있습니다.")
            return

        if self.lbox_item.findItems(self.streamer, Qt.MatchExactly):
            QMessageBox.information(self, "Error", "이미 등록된 스트리머입니다.")
            self.streamer_edit.setText("")
            return

        req = requests.get("https://api.twitch.tv/helix/users?login=" + self.streamer, headers={"Client-ID": client_id, "Authorization": "Bearer " + access_token})
        json_data = json.loads(req.text)

        if len(json_data["data"]) == 0:
            QMessageBox.information(self, "Error", "존재하지 않는 스트리머입니다.")
            return
        else:
            query = self.streamer_edit.text()
            self.streamer_edit.setText("")
            self.lbox_item.addItem(query)

            streamer = query
            streamer_id = json_data["data"][0]["id"]

            with open("streamer_list.pickle", 'rb') as f:
                streamer_list = pickle.load(f)
            
            streamer_list.extend(streamer.split())

            with open("streamer_list.pickle", 'wb') as f:
                pickle.dump(streamer_list, f)

            # 스레드 이름을 streamer_id로 설정
            threading.Thread(target=self.stream_record, args=(streamer, streamer_id), name=streamer_id).start()

            self.console_print(self.streamer + "님 등록 완료")

    def Lbox_itemSelectionChange(self):        
        item = self.lbox_item.currentItem()
        if(item == None):
            self.btn_remove.setEnabled(False)
        else:
            self.btn_remove.setEnabled(True)

    def Btn_removeClick(self):
        selected_streamer = self.lbox_item.currentItem().text()

        with open("streamer_list.pickle", 'rb') as f:
            streamer_list = pickle.load(f)
        
        streamer_list.remove(selected_streamer.lower())

        with open("streamer_list.pickle", 'wb') as f:
            pickle.dump(streamer_list, f)

        self.lbox_item.takeItem(self.lbox_item.currentRow())
        self.console_print(selected_streamer + "님 등록해제 완료")

    """
    def Btn_startClick(self):
        self.btn_start.setEnabled(False)
        # background_process thread 시작
        threading.Thread(target=self.background_process, name="background_process").start()

        self.console_print("프로세스 시작됨")
        self.btn_stop.setEnabled(True)
        return

    def Btn_stopClick(self):
        self.btn_stop.setEnabled(False)
        # background_process thread 강제로 종료


        self.console_print("프로세스 종료됨")
        self.btn_start.setEnabled(True)
        return

    def background_process(self):
        while True:
            time.sleep(1)
    """


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())
    