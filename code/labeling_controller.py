"""
프레임 미리보기에서 클릭으로 라벨 생성
"""
from __future__ import annotations

import os

import cv2
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QTableWidget, QTableWidgetItem

from .geometry import compute_display_geometry, widget_to_image_coords
from .state import ProjectState

MARKER_COLOR_BGR = (0, 0, 255) 
MARKER_RADIUS = 2  


class LabelingController:
    def __init__(self, frame_box: QLabel, label_table: QTableWidget):
        # 어느 라벨(화면)/표에 그릴지만 여기서 받고, state는 나중에 bind()로 따로 연결
        self._frame_box = frame_box
        self._label_table = label_table
        self._state: ProjectState | None = None

    # frame_box, label_table 같은 위젯 요소와 달리, 
    # ProjectState(bodyparts, joints...) -> state(데이터)는 따로 bind 함수로 받음 
    # 나중에 데이터만 따로 보기 편하게 
    def bind(self, state: ProjectState) -> None:
        self._state = state

    def show_frame(self, frame_number: int) -> None:
        self._state.current_frame_number = frame_number
        self._redraw()

    def handle_click(self, widget_x: int, widget_y: int) -> None:
        state = self._state
        if state is None or state.current_frame_number == 0:
            return  # 아직 라벨링 시작 전이면 무시

        frame = cv2.imread(self._current_frame_path())
        if frame is None:
            return
        height, width = frame.shape[:2]
        # 화면에서 클릭한 위치를 이미지 안 실제 픽셀 좌표로 변환
        geometry = compute_display_geometry(width, height, self._frame_box.width(), self._frame_box.height())
        image_coords = widget_to_image_coords(widget_x, widget_y, geometry)
        if image_coords is None:
            return  # 이미지 바깥을 클릭했으면 무시

        row = state.bodyparts[state.current_frame_number - 1]
        # 아직 채워지지 않은(0,0) 첫 번째 조인트 자리를 찾음 -> 클릭할 때마다 다음 조인트가 순서대로 채워짐
        empty_slot = next((i for i in range(0, len(row), 2) if row[i] == 0 and row[i + 1] == 0), None)
        if empty_slot is not None:
            row[empty_slot], row[empty_slot + 1] = image_coords

        self._redraw()

    def delete_last_label(self) -> None:
        state = self._state
        if state is None or state.current_frame_number == 0:
            return

        row = state.bodyparts[state.current_frame_number - 1]
        # 채워진 좌표들 중 마지막 것만 찾아서 0으로 되돌림
        filled = [i for i in range(0, len(row), 2) if row[i] or row[i + 1]]
        if filled:
            i = filled[-1]
            row[i] = 0
            row[i + 1] = 0

        self._redraw()

    def _current_frame_path(self) -> str:
        # 지금 프레임 이미지 경로 조합
        state = self._state
        name = state.extracted_frame_names[state.current_frame_number - 1]
        return os.path.join(state.labeled_data_dir, name)

    def _redraw(self) -> None:
        # 이미지 불러오기 -> 지금까지 찍힌 좌표마다 원 그리기 -> 화면 표시 -> table 갱신
        state = self._state
        frame = cv2.imread(self._current_frame_path())
        if frame is None:
            return

        for x, y in state.labeled_coords_for_frame(state.current_frame_number):
            cv2.circle(frame, (x, y), MARKER_RADIUS, MARKER_COLOR_BGR, -1)

        self._show_pixmap(frame)
        self._refresh_table()

    def _show_pixmap(self, frame) -> None:
        # cv2 이미지를 Qt가 그릴 수 있는 형태로 변환해서 라벨에 붙임 
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = rgb.shape
        qimage = QtGui.QImage(rgb.data, width, height, width * channels, QtGui.QImage.Format_RGB888).copy()
        pixmap = QtGui.QPixmap.fromImage(qimage)
        self._frame_box.setPixmap(pixmap.scaled(self._frame_box.width(), self._frame_box.height(), Qt.KeepAspectRatio))
        self._frame_box.setAlignment(Qt.AlignCenter)

    def _refresh_table(self) -> None:
        # 오른쪽 조인트 좌표 표(LabeltableWidget)를 조인트 이름 + 좌표로 채움
        state = self._state
        joints = state.joints
        self._label_table.clearContents()
        self._label_table.setRowCount(len(joints))

        row = state.bodyparts[state.current_frame_number - 1]
        for i, joint_name in enumerate(joints):
            x, y = row[i * 2], row[i * 2 + 1]
            self._label_table.setItem(i, 0, QTableWidgetItem(f"{x},{y}"))
            self._label_table.setItem(i, 1, QTableWidgetItem(joint_name))
