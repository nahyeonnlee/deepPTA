"""
실제 이미지 픽셀 좌표 ↔ 클릭 화면 위젯 좌표 변환
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayGeometry:
    scale: float
    x_offset: float
    y_offset: float
    display_width: float
    display_height: float


def compute_display_geometry(image_width: int, image_height: int, box_width: int, box_height: int) -> DisplayGeometry:
    #image_width x image_height 크기 이미지를 Qt.KeepAspectRatio로 라벨 안에 그렸을 때의 정보
    if image_width <= 0 or image_height <= 0 or box_width <= 0 or box_height <= 0:
        raise ValueError("widths and heights must be positive")

    scale = min(box_width / image_width, box_height / image_height)
    display_width = image_width * scale
    display_height = image_height * scale
    x_offset = (box_width - display_width) / 2
    y_offset = (box_height - display_height) / 2
    return DisplayGeometry(scale, x_offset, y_offset, display_width, display_height)


def widget_to_image_coords(widget_x: float, widget_y: float, geometry: DisplayGeometry) -> tuple[int, int] | None:
    # 라벨 안에서의 클릭 위치를 이미지 픽셀 좌표로 변환 클릭이 이미지 바깥 여백 쪽이면 None 반환
    if not (geometry.x_offset <= widget_x <= geometry.x_offset + geometry.display_width):
        return None
    if not (geometry.y_offset <= widget_y <= geometry.y_offset + geometry.display_height):
        return None

    image_x = int((widget_x - geometry.x_offset) / geometry.scale)
    image_y = int((widget_y - geometry.y_offset) / geometry.scale)
    return image_x, image_y
