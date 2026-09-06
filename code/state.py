"""
여러 창이 공유하는 프로젝트 상태 
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


# @dataclass 데코레이터로 데이터만 담는 클래스를 표시해두면 __init__을 자동으로 만들어줌
@dataclass
class VideoEntry:
    #영상 하나의 정보 (VideotableWidget의 한 행에 해당)
    path: str
    frame_count: int
    fps: int


@dataclass
class ProjectState:
    #DeepPTA 세션 하나가 여러 창 사이에 공유해야 하는 것들

    videos: list[VideoEntry] = field(default_factory=list)
    selected_video_index: int = 0

    # Label Option / Frame Extract 창에서 입력한 값들
    scorer: str = ""
    joints: list[str] = field(default_factory=list)
    frames_to_extract: int = 0

    labeled_data_dir: str = ""
    extracted_frame_names: list[str] = field(default_factory=list)
    current_frame_number: int = 0  # extracted_frame_names 안에서의 1부터 시작하는 인덱스

    # bodyparts[프레임 인덱스][조인트 인덱스 * 2 : 조인트 인덱스 * 2 + 2] = (x, y)
    # 예: 조인트가 nose, tail 2개면 한 행이 [nose_x, nose_y, tail_x, tail_y]
    bodyparts: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), dtype=int))

    @property
    def selected_video(self) -> VideoEntry | None:
        # 인덱스가 범위를 벗어나도(영상이 없는 등) 에러 대신 None을 반환하도록 방어
        if 0 <= self.selected_video_index < len(self.videos):
            return self.videos[self.selected_video_index]
        return None

    def reset_labels_for(self, frame_count: int) -> None:
        # 새로 프레임을 추출하거나 조인트 개수가 바뀌면 bodyparts를 다시 만들고 전부 0으로 초기화
        self.bodyparts = np.zeros((frame_count, len(self.joints) * 2), dtype=int)
        self.current_frame_number = 0

    def labeled_coords_for_frame(self, frame_number: int) -> list[tuple[int, int]]:
        #1부터 시작하는 프레임 번호에 대해, 지금까지 기록된(0이 아닌) (x, y) 좌표 쌍들
        row = self.bodyparts[frame_number - 1]
        return [(int(row[i]), int(row[i + 1])) for i in range(0, len(row), 2) if row[i] or row[i + 1]]
