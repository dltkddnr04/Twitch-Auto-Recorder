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
from PyQt5.QtCore import Qt, pyqtSignal
from function import (twitch_api, update)
from function.recording_service import RecordingWorker, validated_channel

current_version = "1.3.0"

# streamer_list.pikle 파일이 없으면 생성
if not os.path.isfile("streamer_list.pickle"):
    with open("streamer_list.pickle", "wb") as f:
        pickle.dump([], f)

class MyApp(QWidget):
    log_signal = pyqtSignal(str)
    update_signal = pyqtSignal(object)

    def __init__(self):
        if not os.path.isfile("setup.pickle"):
            extension = 'ts'
            with open("setup.pickle", "wb") as f:
                pickle.dump(extension, f)

        with open("setup.pickle", "rb") as f:
            self.extension = pickle.load(f)
        self.workers = {}
        self.worker_threads = {}
        super().__init__()
        self.log_signal.connect(self.console_print)
        self.update_signal.connect(self._on_update_result)
        self.initUI()

        # Actual TS/fMP4 container is detected; optional remux preserves the raw source on failure.

    def initUI(self):
        grid = QGridLayout()
        grid.addWidget(self.createSetupGroup(), 0, 0)
        grid.addWidget(self.createTerminalGroup(), 1, 0)

        self.setLayout(grid)

        # self.setWindowIcon(QIcon('resource/logo.png'))
        self.setWindowTitle('트위치 자동 녹화기 ' + current_version)
        self.resize(600, 400)
        self.show()


        threading.Thread(target=self.update_check, daemon=True).start()
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
        
    def _start_worker(self, streamer):
        if streamer in self.workers:
            return
        worker = RecordingWorker(streamer, extension=self.extension, log=self.log_signal.emit)
        thread = threading.Thread(target=worker.run, name=streamer, daemon=True)
        self.workers[streamer] = worker
        self.worker_threads[streamer] = thread
        thread.start()

    def _stop_worker(self, streamer):
        worker = self.workers.pop(streamer, None)
        self.worker_threads.pop(streamer, None)
        if worker:
            worker.stop()

    def _save_streamers(self):
        with open("streamer_list.pickle", "wb") as f:
            pickle.dump(list(self.workers), f)

    def start_program(self):
        self.console_print("프로그램 시작")
        try:
            with open("streamer_list.pickle", "rb") as f:
                streamers = pickle.load(f)
            if not isinstance(streamers, list):
                raise ValueError("Invalid streamer list")
        except (OSError, ValueError, pickle.PickleError, EOFError) as exc:
            self.console_print("스트리머 목록 읽기 실패: " + str(exc))
            streamers = []
        for name in streamers:
            try:
                streamer = validated_channel(name)
                if streamer not in self.workers:
                    self.lbox_item.addItem(streamer)
                    self._start_worker(streamer)
            except (ValueError, TypeError) as exc:
                self.console_print("잘못된 채널 아이디: " + str(exc))
        self._save_streamers()

    def closeEvent(self, event):
        threads = list(self.worker_threads.values())
        for worker in list(self.workers.values()):
            worker.stop()
        deadline = time.monotonic() + 15
        for thread in threads:
            thread.join(timeout=max(0, deadline - time.monotonic()))
        event.accept()

    def update_check(self):
        # Network I/O happens on a worker; only the main thread updates Qt.
        try:
            latest_version = update.get_latest_version()
            self.update_signal.emit((latest_version, None))
        except (requests.RequestException, ValueError, KeyError) as exc:
            self.update_signal.emit((None, str(exc)))

    def _on_update_result(self, result):
        latest_version, error = result
        if error:
            self.console_print("업데이트 확인 실패: " + error)
        elif update.compare_version(current_version, latest_version):
            QMessageBox.information(self, "업데이트 알림",
                "현재 " + latest_version + " 버전이 사용가능합니다.\n"
                "https://github.com/dltkddnr04/Twitch-Auto-Recorder/releases")

    def Btn_addClick(self):
        streamer = self.streamer_edit.text().strip().lower()
        try:
            streamer = validated_channel(streamer)
        except ValueError as exc:
            QMessageBox.information(self, "경고", str(exc))
            return
        if self.radio_option1.isChecked():
            self.add_streamer(streamer, None)
            return

        # Followed channels require a user OAuth token with user:read:follows.
        try:
            twitch_api.get_header_online()
            user_id = twitch_api.get_id_from_login(streamer)
            follow_list = twitch_api.get_follow_data(user_id)
        except (requests.RequestException, ValueError, KeyError, IndexError, RuntimeError) as exc:
            QMessageBox.information(self, "API 오류", "팔로우 목록 조회 실패: " + str(exc))
            return
        if QMessageBox.question(
            self, "Warning", "기존 스트리머 등록을 모두 해제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        target_names = []
        for followed in follow_list:
            try:
                name = validated_channel(followed["to_login"])
                if name not in target_names:
                    target_names.append(name)
            except (ValueError, KeyError):
                continue
        for name in list(self.workers):
            if name not in target_names:
                self._stop_worker(name)
        self.lbox_item.clear()
        for name in target_names:
            self.lbox_item.addItem(name)
            if name not in self.workers:
                self._start_worker(name)
        self._save_streamers()
        self.streamer_edit.clear()
        self.radio_option1.setChecked(True)
        self.console_print(f"팔로우한 스트리머 {len(self.workers)}명 등록 완료")

    def add_streamer(self, streamer, streamer_id):
        streamer = validated_channel(streamer)
        if streamer in self.workers:
            QMessageBox.information(self, "경고", "이미 등록된 스트리머입니다.")
            return
        self.lbox_item.addItem(streamer)
        self._start_worker(streamer)
        self._save_streamers()
        self.streamer_edit.clear()
        self.console_print(streamer + "님 등록 완료")

    def Lbox_itemSelectionChange(self):        
        item = self.lbox_item.currentItem()
        if(item == None):
            self.btn_remove.setEnabled(False)
        else:
            self.btn_remove.setEnabled(True)

    def Btn_removeClick(self):
        selected = self.lbox_item.currentItem()
        if selected is None:
            return
        name = selected.text()
        self._stop_worker(name)
        self.lbox_item.takeItem(self.lbox_item.currentRow())
        self._save_streamers()
        self.radio_option1.setChecked(True)
        self.maunal_mode()
        self.console_print(name + "님 등록해제 완료")

    def maunal_mode(self):
        self.title_label.setText("스트리머 영문 닉네임")
        return

    def automatic_mode(self):
        self.title_label.setText("본인의 영문 닉네임")
        return

    def extension_ts(self):
        self.extension = 'ts'
        for worker in self.workers.values():
            worker.extension = self.extension
        with open("setup.pickle", 'wb') as f:
            pickle.dump(self.extension, f)
        return

    def extension_mp4(self):
        self.extension = 'mp4'
        for worker in self.workers.values():
            worker.extension = self.extension
        with open("setup.pickle", 'wb') as f:
            pickle.dump(self.extension, f)
        return

    def extension_mkv(self):
        self.extension = 'mkv'
        for worker in self.workers.values():
            worker.extension = self.extension
        with open("setup.pickle", 'wb') as f:
            pickle.dump(self.extension, f)
        return

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())