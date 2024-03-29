import requests
import json
import time
import sys
import threading
import pickle
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QTextBrowser, QGridLayout, QGroupBox, QLabel, QMessageBox, QRadioButton)
import PyQt5.QtWidgets as qtwid
from PyQt5.QtCore import Qt
from function import (twitch_api, update, recorder)

current_version = "1.3.0"

# streamer_list.pikle 파일이 없으면 생성
if not os.path.isfile("streamer_list.pickle"):
    with open("streamer_list.pickle", "wb") as f:
        pickle.dump([], f)

class MyApp(QWidget):
    def __init__(self):
        if not os.path.isfile("setup.pickle"):
            extension = 'ts'
            with open("setup.pickle", "wb") as f:
                pickle.dump(extension, f)

        with open("setup.pickle", "rb") as f:
            self.extension = pickle.load(f)
        super().__init__()
        self.initUI()

        QMessageBox.information(self, "경고", "ts 이외의 파일형식을 사용할경우 녹화가 중간에 중단될시 파일이 유실될 수 있습니다.\n컴퓨터나 프로그램이 강제로 종료될 가능성이 있는경우 ts 파일로 녹화한 후에 인코딩하는것을 추천합니다.")

    def initUI(self):
        grid = QGridLayout()
        grid.addWidget(self.createSetupGroup(), 0, 0)
        grid.addWidget(self.createTerminalGroup(), 1, 0)

        self.setLayout(grid)

        # self.setWindowIcon(QIcon('resource/logo.png'))
        self.setWindowTitle('트위치 자동 녹화기 ' + current_version)
        self.resize(600, 400)
        self.show()

        try:
            twitch_api.get_header_online()

        except:
            QMessageBox.information(self, "경고", "인터넷에 연결되어있지 않습니다.\n인터넷 연결을 확인해주세요.")
            exit()

        self.update_check()
        self.start_program()

    def createSetupGroup(self):
        groupbox = QGroupBox('설정')
        grid = QGridLayout()

        self.streamer_edit = qtwid.QLineEdit(self)
        self.save_btn = qtwid.QPushButton("추가",self)
        self.lbox_item = qtwid.QListWidget(self)

        self.streamer_edit.setToolTip('스트리머의 영문 닉네임을 입력하세요')
        self.title_label = QLabel("스트리머 영문 닉네임")

        #grid.addWidget(self.radio_group(), 1, 0, 1, 2)
        #grid.addWidget(self.extension_radio_group(), 0, 0, 1, 2)

        grid.addWidget(self.radio_group(), 0, 0, )
        grid.addWidget(self.extension_radio_group(), 0, 1)

        grid.addWidget(self.title_label, 2, 0)
        grid.addWidget(self.streamer_edit, 3, 0)
        grid.addWidget(self.save_btn, 3, 1)
        grid.addWidget(self.lbox_item, 4, 0)
        grid.addWidget(self.btn_group(), 4, 1)

        self.save_btn.clicked.connect(self.Btn_addClick)        
        self.lbox_item.itemSelectionChanged.connect(self.Lbox_itemSelectionChange)

        groupbox.setLayout(grid)
        return groupbox

    def btn_group(self):
        groupbox = QGroupBox()
        grid = QGridLayout()

        self.btn_remove = qtwid.QPushButton("등록해제",self)
        grid.addWidget(self.btn_remove, 0, 0)
        self.btn_remove.clicked.connect(self.Btn_removeClick)
        self.btn_remove.setEnabled(False)

        groupbox.setLayout(grid)
        return groupbox
    
    def radio_group(self):
        groupbox = QGroupBox()
        grid = QGridLayout()

        self.radio_option1 = QRadioButton('스트리머 수동 등록', self)
        self.radio_option2 = QRadioButton('팔로우한 사람 등록', self)

        grid.addWidget(self.radio_option1, 0, 0)
        grid.addWidget(self.radio_option2, 0, 1)

        self.radio_option1.setChecked(True)
        self.radio_option1.clicked.connect(self.maunal_mode)
        self.radio_option2.clicked.connect(self.automatic_mode)

        groupbox.setLayout(grid)
        return groupbox

    def extension_radio_group(self):
        groupbox = QGroupBox()
        grid = QGridLayout()

        self.extension_radio_option1 = QRadioButton('ts', self)
        self.extension_radio_option2 = QRadioButton('mp4', self)
        self.extension_radio_option3 = QRadioButton('mkv', self)

        grid.addWidget(self.extension_radio_option1, 0, 0)
        grid.addWidget(self.extension_radio_option2, 1, 0)
        grid.addWidget(self.extension_radio_option3, 2, 0)

        if self.extension == 'ts':
            self.extension_radio_option1.setChecked(True)
        elif self.extension == 'mp4':
            self.extension_radio_option2.setChecked(True)
        elif self.extension == 'mkv':
            self.extension_radio_option3.setChecked(True)
        
        self.extension_radio_option1.clicked.connect(self.extension_ts)
        self.extension_radio_option2.clicked.connect(self.extension_mp4)
        self.extension_radio_option3.clicked.connect(self.extension_mkv)

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
        
    def stream_record(self, streamer, streamer_id):
        if streamer_id == None:
            streamer_id = twitch_api.get_id_from_login(streamer)
        while True:
            if twitch_api.get_stream_data(streamer_id):
                self.console_print(streamer + "님 방송 녹화 시작")
                recorder.download_stream_m3u8_legacy(streamer, self.extension)
                self.console_print(streamer + "님 방송 녹화 종료")
            if not self.lbox_item.findItems(streamer, Qt.MatchExactly):
                break
            time.sleep(10)

    def start_program(self):
        self.console_print("프로그램 시작")

        with open("streamer_list.pickle", 'rb') as f:
            streamer_list = pickle.load(f)
            if streamer_list != []:
                self.console_print("스트리머 불러오기 완료")

                for streamer in streamer_list:
                    self.lbox_item.addItem(streamer)

                    threading.Thread(target=self.stream_record, args=(streamer, None), name=streamer).start()

    def update_check(self):
        # 업데이트 확인 코드
        try:
            latest_version = update.get_latest_version()
            if update.compare_version(current_version, latest_version):
                QMessageBox.information(self, "업데이트 알림", "현재 " + latest_version + " 버전이 사용가능합니다.\n업데이트 주소:\nhttps://github.com/dltkddnr04/Twitch-Auto-Recorder/releases")

        except:
            QMessageBox.information(self, "경고", "인터넷에 연결되어있지 않습니다.\n인터넷 연결을 확인해주세요.")

    def Btn_addClick(self):
        streamer = self.streamer_edit.text()
        if streamer == "":
            QMessageBox.information(self, "경고", "이름이 비어있습니다.")

        if self.radio_option1.isChecked():
            if self.lbox_item.findItems(streamer, Qt.MatchExactly):
                QMessageBox.information(self, "경고", "이미 등록된 스트리머입니다.")
                self.streamer_edit.setText("")
            else:
                self.add_streamer(streamer, None)

        else:
            # 경고창으로 물어보기
            if QMessageBox.question(self, "Warning", "기존의 모든 스트리머가 등록해제됩니다.\n 계속하시겠습니까?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                user = self.streamer_edit.text()
                if not twitch_api.check_user_exists(user):
                    QMessageBox.information(self, "경고", "존재하지 않는 유저입니다.")
                else:
                    # lbox_item 전부 삭제하기
                    for i in range(self.lbox_item.count()):
                        self.lbox_item.takeItem(0)

                    streamer_list = []
                    with open("streamer_list.pickle", 'wb') as f:
                        pickle.dump(streamer_list, f)

                    self.streamer_edit.setText("")

                    self.console_print("전체 스트리머 등록 해제 완료")

                    user_id = twitch_api.get_id_from_login(user)

                    follow_list = twitch_api.get_follow_data(user_id)
                    # follow_list에 스트리머 닉네임과 아이디 저장
                    for streamer in follow_list:
                        if not self.lbox_item.findItems(streamer['to_login'], Qt.MatchExactly):
                            self.add_streamer(streamer['to_login'], streamer['to_id'])

                    if not follow_list:
                        self.console_print("팔로우한 스트리머가 없습니다.")
                    else:
                        self.console_print("팔로우한 스트리머 등록 완료")
            else:
                QMessageBox.information(self, "경고", "취소되었습니다.")
            
            self.radio_option1.setChecked(True)
        return

    def add_streamer(self, streamer, streamer_id):
        if streamer_id == None:
            if not twitch_api.check_user_exists(streamer):
                QMessageBox.information(self, "경고", "존재하지 않는 스트리머입니다.")
                return
            else:
                self.streamer_edit.setText("")
                streamer_id = twitch_api.get_id_from_login(streamer)

        
        self.lbox_item.addItem(streamer)

        with open("streamer_list.pickle", 'rb') as f:
            streamer_list = pickle.load(f)
            
        streamer_list.extend(streamer.split())

        with open("streamer_list.pickle", 'wb') as f:
            pickle.dump(streamer_list, f)

        # 스레드 이름을 streamer_id로 설정
        threading.Thread(target=self.stream_record, args=(streamer, streamer_id), name=streamer).start()

        self.console_print(streamer + "님 등록 완료")
        return

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

        self.radio_option1.setChecked(True)
        self.maunal_mode()

        self.lbox_item.takeItem(self.lbox_item.currentRow())
        self.console_print(selected_streamer + "님 등록해제 완료")
        return

    def maunal_mode(self):
        self.title_label.setText("스트리머 영문 닉네임")
        return

    def automatic_mode(self):
        self.title_label.setText("본인의 영문 닉네임")
        return

    def extension_ts(self):
        self.extension = 'ts'
        with open("setup.pickle", 'wb') as f:
            pickle.dump(self.extension, f)
        return

    def extension_mp4(self):
        self.extension = 'mp4'
        with open("setup.pickle", 'wb') as f:
            pickle.dump(self.extension, f)
        return

    def extension_mkv(self):
        self.extension = 'mkv'
        with open("setup.pickle", 'wb') as f:
            pickle.dump(self.extension, f)
        return

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())