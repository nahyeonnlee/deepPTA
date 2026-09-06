"""
메인 윈도우: ``ui/DeepPTA.ui``의 위젯들을 이 패키지 안의 조각들에 연결
조립/이벤트 연결 담당 클래스 — 영상 재생, 라벨링, CSV export, DeepLabCut 호출은 전부 각자 모듈에 있음
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from PyQt5 import QtGui, uic
from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QTableWidgetItem

from .analysis import LikelihoodChartWidget
from .dialogs import FrameExtractWindow, LabelOptionWindow
from .dlc import extract_frames_for_labeling, make_prediction, save_collected_data, train_model
from .labeling_controller import LabelingController
from .state import ProjectState, VideoEntry
from .video_player import VideoPlayer

UI_DIR = Path(__file__).resolve().parent.parent / "ui"
MainWindowUi, _ = uic.loadUiType(str(UI_DIR / "DeepPTA.ui"))

# .ui 파일의 아이콘 경로는 프로세스의 현재 작업 디렉터리(cwd) 기준으로 해석되므로 앱을 프로젝트 루트에서 실행해야 함
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"


class MainWindow(QMainWindow, MainWindowUi):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("DeepPTA")

        self.state = ProjectState()
        self.video_player = VideoPlayer(self)
        self.analysis_video_player = VideoPlayer(self)
        self.labeling_controller = LabelingController(self.Framebox, self.LabeltableWidget)
        self.labeling_controller.bind(self.state)
        self.analysis_widget = LikelihoodChartWidget()

        self._child_windows: list = []  # 팝업창들이 가비지 컬렉션되지 않도록 참조를 붙잡아둠

        self._connect_signals()
        self._set_playback_icons()

    def _set_playback_icons(self) -> None:
        self.playButton.setIcon(QtGui.QIcon(str(ASSETS_DIR / "play.png")))
        self.stopButton.setIcon(QtGui.QIcon(str(ASSETS_DIR / "pause.png")))
        self.forwardButton.setIcon(QtGui.QIcon(str(ASSETS_DIR / "forward.png")))
        self.rewindButton.setIcon(QtGui.QIcon(str(ASSETS_DIR / "rewind.png")))
        self.AnalysisPlayButton.setIcon(QtGui.QIcon(str(ASSETS_DIR / "play.png")))
        self.AnalysisStopButton.setIcon(QtGui.QIcon(str(ASSETS_DIR / "pause.png")))
        self.AnalysisForwardButton.setIcon(QtGui.QIcon(str(ASSETS_DIR / "forward.png")))
        self.AnalysisRewindButton.setIcon(QtGui.QIcon(str(ASSETS_DIR / "rewind.png")))

    def _connect_signals(self) -> None:
        self.AddButton.clicked.connect(self._add_video)
        self.RemoveButton.clicked.connect(self._remove_video)
        self.playButton.clicked.connect(self.video_player.play)
        self.stopButton.clicked.connect(self.video_player.stop)
        self.forwardButton.clicked.connect(lambda: self.video_player.seek_relative(100))
        self.rewindButton.clicked.connect(lambda: self.video_player.seek_relative(-100))
        self.VideoSlider.sliderMoved.connect(self.video_player.seek_to)
        self.tableWidget.cellClicked.connect(self._select_video)
        self.tableWidget.cellDoubleClicked.connect(self._select_video)

        self.video_player.frame_ready.connect(self._show_video_frame)
        self.video_player.position_changed.connect(self._update_slider)
        self.video_player.time_changed.connect(self._update_time_labels)

        self.Frame_Extract.triggered.connect(self._open_frame_extract)
        self.Label_Option.triggered.connect(self._open_label_option)
        self.actionAnalyzeVideo.triggered.connect(self._open_analysis)

        self.VideotableWidget.cellClicked.connect(self._open_labeled_frames_folder)
        self.VideotableWidget.cellDoubleClicked.connect(self._open_labeled_frames_folder)
        self.NextButton.clicked.connect(self._next_frame)
        self.BackButton.clicked.connect(self._back_frame)
        self.DeleteButton.clicked.connect(self.labeling_controller.delete_last_label)
        self.SaveButton.clicked.connect(self._save_labels)
        self.TrainModelButton.clicked.connect(self._train_model)
        self.MakePredictionButton.clicked.connect(self._make_prediction)

        self.Framebox.installEventFilter(self)

        self.analysis_video_player.frame_ready.connect(self._show_analysis_frame)
        self.AnalysisButton.clicked.connect(self._open_analysis_video)
        self.AnalysisPlayButton.clicked.connect(self.analysis_video_player.play)
        self.AnalysisStopButton.clicked.connect(self.analysis_video_player.stop)
        self.AnalysisForwardButton.clicked.connect(lambda: self.analysis_video_player.seek_relative(100))
        self.AnalysisRewindButton.clicked.connect(lambda: self.analysis_video_player.seek_relative(-100))
        self.AnalysisSlider.sliderMoved.connect(self.analysis_video_player.seek_to)
        self.analysis_video_player.position_changed.connect(self._update_analysis_slider)

    def eventFilter(self, obj, event):
        if obj is self.Framebox and event.type() == QEvent.MouseButtonPress:
            self.labeling_controller.handle_click(event.x(), event.y())
            return True
        return super().eventFilter(obj, event)

    # ---- 영상 목록 -----------------------------------------------------

    def _add_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open file", "./")
        if not path:
            return
        frame_count, fps = self.video_player.load(path)
        self.state.videos.append(VideoEntry(path, frame_count, fps))
        self.state.selected_video_index = len(self.state.videos) - 1

        for table in (self.tableWidget, self.VideotableWidget, self.ps_widget):
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(path))
        row = self.tableWidget.rowCount() - 1
        self.tableWidget.setItem(row, 1, QTableWidgetItem(str(frame_count)))
        self.tableWidget.setItem(row, 2, QTableWidgetItem(str(fps)))

        self.VideoSlider.setRange(0, frame_count)
        self.VideoSlider.setSingleStep(max(1, frame_count // 100))
        self.video_player.play()

    def _remove_video(self) -> None:
        row = self.tableWidget.currentRow()
        if row < 0:
            return
        self.tableWidget.removeRow(row)
        self.VideotableWidget.removeRow(row)
        self.ps_widget.removeRow(row)
        del self.state.videos[row]

        if self.state.videos:
            self.state.selected_video_index = max(0, row - 1)
            self.video_player.load(self.state.selected_video.path)
        else:
            self.state.selected_video_index = 0
            self.video_player.stop()

    def _select_video(self, row: int, _column: int) -> None:
        self.state.selected_video_index = row
        self.video_player.load(self.state.videos[row].path)

    def _show_video_frame(self, image) -> None:
        pixmap = QtGui.QPixmap.fromImage(image)
        self.Vbox.setPixmap(pixmap.scaled(self.Vbox.width(), self.Vbox.height(), Qt.KeepAspectRatio))
        self.Vbox.setAlignment(Qt.AlignCenter)

    def _update_slider(self, current_frame: int, total_frames: int) -> None:
        self.VideoSlider.blockSignals(True)
        self.VideoSlider.setMaximum(total_frames)
        self.VideoSlider.setValue(current_frame)
        self.VideoSlider.blockSignals(False)

    def _update_time_labels(self, elapsed: str, total: str) -> None:
        self.timelabel.setText(elapsed)
        self.ftimelabel.setText(total)

    # ---- 프레임 추출 -------------------------------------------------

    def _open_frame_extract(self) -> None:
        if not self.state.videos:
            return
        window = FrameExtractWindow(self.state, self._extract_frames)
        self._child_windows.append(window)
        window.show()

    def _extract_frames(self) -> None:
        video = self.state.selected_video
        try:
            labeled_dir, frame_names = extract_frames_for_labeling(
                self.video_player.capture,
                video.path,
                video.frame_count,
                self.state.frames_to_extract,
                self.state.scorer,
            )
        except Exception as exc:
            QMessageBox.warning(self, "Frame extraction failed", str(exc))
            return
        self.state.labeled_data_dir = labeled_dir
        self.state.extracted_frame_names = frame_names
        self.state.reset_labels_for(len(frame_names))

    # ---- 라벨링 ----------------------------------------------------------

    def _open_label_option(self) -> None:
        window = LabelOptionWindow(self.state, self._on_joints_finalized)
        self._child_windows.append(window)
        window.show()

    def _on_joints_finalized(self) -> None:
        if self.state.extracted_frame_names:
            self.state.reset_labels_for(len(self.state.extracted_frame_names))
            self._show_frame(1)

    def _open_labeled_frames_folder(self, *_args) -> None:
        video = self.state.selected_video
        start_dir = os.path.dirname(video.path) if video else "./"
        folder = QFileDialog.getExistingDirectory(self, "Open labeled-data folder", start_dir)
        if not folder:
            return

        self.state.labeled_data_dir = folder
        self.state.extracted_frame_names = sorted(os.listdir(folder))
        self.state.reset_labels_for(len(self.state.extracted_frame_names))

        self.FrametableWidget.setRowCount(len(self.state.extracted_frame_names))
        for i, name in enumerate(self.state.extracted_frame_names):
            self.FrametableWidget.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.FrametableWidget.setItem(i, 1, QTableWidgetItem(name))

        row = self.VideotableWidget.currentRow()
        if row >= 0 and video is not None:
            self.VideotableWidget.setItem(row, 1, QTableWidgetItem(str(len(self.state.extracted_frame_names))))
            self.VideotableWidget.setItem(row, 2, QTableWidgetItem(str(video.frame_count)))

        self.Tlabel.setText(f"/  {len(self.state.extracted_frame_names)}")
        if self.state.extracted_frame_names:
            self._show_frame(1)

    def _show_frame(self, frame_number: int) -> None:
        self.Nlabel.setText(str(frame_number))
        self.labeling_controller.show_frame(frame_number)

    def _next_frame(self) -> None:
        if self.state.current_frame_number < len(self.state.extracted_frame_names):
            self._show_frame(self.state.current_frame_number + 1)

    def _back_frame(self) -> None:
        if self.state.current_frame_number > 1:
            self._show_frame(self.state.current_frame_number - 1)

    def _save_labels(self) -> None:
        if not self.state.extracted_frame_names:
            return
        filepath = os.path.join(self.state.labeled_data_dir, f"CollectedData_{self.state.scorer}.csv")
        try:
            save_collected_data(
                filepath,
                self.state.scorer,
                self.state.joints,
                self.state.selected_video.path,
                self.state.extracted_frame_names,
                self.state.bodyparts,
            )
        except OSError as exc:
            QMessageBox.warning(self, "Save failed", str(exc))

    # ---- 자세 추정(pose estimation) -----------------------------------------------------

    def _train_model(self) -> None:
        config_path, _ = QFileDialog.getOpenFileName(self, "Open config.yaml", "./")
        if not config_path:
            return
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        scorer = str(data.get("scorer", self.state.scorer)).strip()

        try:
            train_model(
                config_path,
                scorer,
                int(self.max_snapshots_to_keep.text()),
                int(self.saveriters.text()),
                int(self.maxiters.text()),
                self.state.joints,
            )
        except Exception as exc:
            QMessageBox.warning(self, "Training failed", str(exc))

    def _make_prediction(self) -> None:
        config_path, _ = QFileDialog.getOpenFileName(self, "Open config.yaml", "./")
        if not config_path:
            return
        try:
            make_prediction(config_path)
        except Exception as exc:
            QMessageBox.warning(self, "Prediction failed", str(exc))

    # ---- 분석(Analysis) -----------------------------------------------------------

    def _open_analysis_video(self) -> None:
        video_path, _ = QFileDialog.getOpenFileName(self, "Open result video", "./", "Video files (*.mp4)")
        if not video_path:
            return
        self.analysis_video_player.load(video_path)
        self.analysis_video_player.play()

        csv_path = video_path.replace("_labeled.mp4", ".csv")
        try:
            self.analysis_widget.plot_csv(csv_path)
            pixmap = self.analysis_widget.grab()
            # 화면 맞추기
            dpr = pixmap.devicePixelRatio() or 1.0
            target_width = round(self.AnalysisGraph.width() * dpr)
            scaled = pixmap.scaledToWidth(target_width, Qt.SmoothTransformation)
            scaled.setDevicePixelRatio(dpr)
            self.AnalysisGraph.setPixmap(scaled)
            self.AnalysisGraph.setAlignment(Qt.AlignCenter)
        except Exception as exc:
            QMessageBox.warning(self, "Analysis failed", str(exc))

    def _show_analysis_frame(self, image) -> None:
        pixmap = QtGui.QPixmap.fromImage(image)
        self.AnalysisVideo.setPixmap(pixmap.scaled(self.AnalysisVideo.width(), self.AnalysisVideo.height(), Qt.KeepAspectRatio))
        self.AnalysisVideo.setAlignment(Qt.AlignCenter)

    def _update_analysis_slider(self, current_frame: int, total_frames: int) -> None:
        self.AnalysisSlider.blockSignals(True)
        self.AnalysisSlider.setMaximum(total_frames)
        self.AnalysisSlider.setValue(current_frame)
        self.AnalysisSlider.blockSignals(False)

    def _open_analysis(self) -> None:
        csv_path, _ = QFileDialog.getOpenFileName(self, "Open prediction CSV", "./", "CSV files (*.csv)")
        if not csv_path:
            return
        try:
            self.analysis_widget.plot_csv(csv_path)
            self.tabWidget.setCurrentWidget(self.analysis_widget)
        except Exception as exc:
            QMessageBox.warning(self, "Analysis failed", str(exc))
