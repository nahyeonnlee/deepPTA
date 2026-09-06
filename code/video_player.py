"""
QTimer 기반 영상 재생
"""
from __future__ import annotations

import cv2
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtGui import QImage


def format_timestamp(total_seconds: float) -> str:
    #시:분:초, 원본 라벨 형식이랑 동일
    total_seconds = max(0, int(total_seconds))
    hours, remainder = divmod(total_seconds, 3600)  
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes}:{seconds}"


def frame_to_qimage(frame) -> QImage:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width, channels = rgb.shape
    image = QImage(rgb.data, width, height, width * channels, QImage.Format_RGB888)
    return image.copy()


class VideoPlayer(QObject):
    """``cv2.VideoCapture`` 하나를 감싸서, 디코딩한 프레임을 타이머로 계속 내보낸다."""

    # 상태가 바뀔 때마다 이 신호들을 쏘고, main_window.py가 connect()로 받아서 화면을 갱신함
    frame_ready = pyqtSignal(QImage)  # 새 프레임 준비
    position_changed = pyqtSignal(int, int)  # 재생 위치 변경 (현재 프레임, 전체 프레임 수)
    time_changed = pyqtSignal(str, str)  # 시간 표시 변경 (경과 시간, 전체 시간)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._capture = cv2.VideoCapture()
        self._timer = QTimer(self)
        # 원본의 while 무한루프 대신 타이머로 재생 — 타이머 간격 사이에 Qt가 다른 이벤트도 처리 가능
        self._timer.timeout.connect(self._advance_and_emit)

    def load(self, path: str) -> tuple[int, int]:
        #path열고 (frame_count, fps) 반환
        self._capture.open(path)
        frame_count = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = int(self._capture.get(cv2.CAP_PROP_FPS))
        self._show_current_frame()
        return frame_count, fps

    @property
    def capture(self) -> cv2.VideoCapture:
        #dlc.py의 extract_frames_for_labeling이 지금 로드된 영상에서 직접 프레임을 읽을 수 있도록 노출해둔 것
        return self._capture

    def play(self) -> None:
        fps = self._capture.get(cv2.CAP_PROP_FPS) or 30
        self._timer.start(int(1000 / fps))  # 한 프레임당 몇 ms마다 실행할지

    def stop(self) -> None:
        self._timer.stop()

    def seek_relative(self, delta_frames: int) -> None:
        current = self._capture.get(cv2.CAP_PROP_POS_FRAMES)
        self.seek_to(int(current) + delta_frames)

    def seek_to(self, frame_number: int) -> None:
        frame_number = max(0, frame_number)
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self._show_current_frame()

    def _advance_and_emit(self) -> None:
        # 타이머가 주기적으로 호출. 영상 끝까지 재생됐으면 처음(0)으로 되돌림
        total = self._capture.get(cv2.CAP_PROP_FRAME_COUNT)
        if self._capture.get(cv2.CAP_PROP_POS_FRAMES) >= total:
            self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self._show_current_frame(advance=True)

    def _show_current_frame(self, advance: bool = False) -> None:
        if advance:
            # 재생 중: 다음 프레임 읽기
            ok, frame = self._capture.read()
        else:
            # 탐색바 이동/일시정지 다시 그리기
            position = self._capture.get(cv2.CAP_PROP_POS_FRAMES)
            ok, frame = self._capture.read()
            if ok:
                self._capture.set(cv2.CAP_PROP_POS_FRAMES, position)
        if not ok:
            return

        self.frame_ready.emit(frame_to_qimage(frame))

        total = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT))
        current = int(self._capture.get(cv2.CAP_PROP_POS_FRAMES))
        self.position_changed.emit(current, total)

        fps = self._capture.get(cv2.CAP_PROP_FPS) or 1
        elapsed = format_timestamp(current / fps)
        total_time = format_timestamp(total / fps)
        self.time_changed.emit(elapsed, total_time)
