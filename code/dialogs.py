'''
Frame Extract & Label Option
'''
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PyQt5 import uic
from PyQt5.QtWidgets import QMessageBox, QWidget

from .state import ProjectState

# 실행 위치랑 무관하게 항상 ui/ 폴더를 찾도록 이 파일 자신의 위치 기준 절대경로로 계산
UI_DIR = Path(__file__).resolve().parent.parent / "ui"
# Qt Designer로 만든 .ui 파일을 파이썬 클래스로 변환
FrameExtractUi, _ = uic.loadUiType(str(UI_DIR / "FrameExtract.ui"))
LabelOptionUi, _ = uic.loadUiType(str(UI_DIR / "LabelOption.ui"))


# QWidget(창의 기본 기능) + FrameExtractUi(.ui로 만든 위젯 설계도) 상속
class FrameExtractWindow(QWidget, FrameExtractUi):
    def __init__(self, state: ProjectState, on_extract: Callable[[], None]):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("Frame Extract Option")
        self._state = state
        # on_extract: 추출 버튼 누르면 실행할 콜백 함수
        self._on_extract = on_extract

        self.ExtractButton.clicked.connect(self._handle_extract)
        video = state.selected_video
        if video:
            self.Selected_label.setText(video.path)

    def _handle_extract(self) -> None:
        # 입력창에서 실험자 이름/프레임 개수를 읽어서 공유 state에 저장
        self._state.scorer = self.Experimenter.text().strip()
        self._state.frames_to_extract = int(self.FrameNumber.text())
        self._on_extract()  # 전달받은 콜백 실행 
        self.extract_ox.setText("Extracted!")


class LabelOptionWindow(QWidget, LabelOptionUi):
    def __init__(self, state: ProjectState, on_finish: Callable[[], None]):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("Label Option")
        self._state = state
        self._on_finish = on_finish  # 조인트 이름 확정되면 실행할 함수를 콜백

        self.EnterButton.clicked.connect(self._handle_enter_count)
        self.FinishButton.clicked.connect(self._handle_finish)

    def _handle_enter_count(self) -> None:
        # 숫자가 아닌 값을 입력해도 앱이 죽지 않고 경고창만 뜨도록 방어
        try:
            joint_count = int(self.Label_lineEdit.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid input", "Enter a whole number for the joint count.")
            return
        if joint_count <= 0:
            QMessageBox.warning(self, "Invalid input", "Joint count must be at least 1.")
            return
        self.Label_tableWidget.setRowCount(joint_count)
        self.LO_text.setText("Set your Joint Name and Connection")

    def _handle_finish(self) -> None:
        joint_count = self.Label_tableWidget.rowCount()
        joints = []
        for i in range(joint_count):
            item = self.Label_tableWidget.item(i, 0)
            # 셀이 비어있으면 item 자체가 None일 수 있어서 존재 여부부터 확인
            name = item.text().strip() if item else ""
            if not name:
                QMessageBox.warning(self, "Missing joint name", f"Row {i + 1} has no joint name.")
                return
            joints.append(name)
        self._state.joints = joints
        self.Finish_label.setText("Finished!")
        self._on_finish()  # main_window.py가 이 시점에 라벨 화면을 다시 그리도록 콜백 실행
