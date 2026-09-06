"""
DeepLabCut 관련:
프로젝트에 프레임 추출하기,
'CollectedData_<scorer>.csv' 저장하기, 
학습/추론 실행
"""
from __future__ import annotations

import csv
import glob
import os
import random
from datetime import datetime
from pathlib import Path

import numpy as np

# 앱을 어디서 실행했는지/원본 영상 위치랑 무관하게 프레임 추출 결과를 이 파일 위치 기준으로 계산 
DEFAULT_PROJECTS_ROOT = str(Path(__file__).resolve().parent.parent / "output")

# deeplabcut 2.3의 TensorFlow 백엔드(`pose_estimation_tensorflow`)는 TensorFlow/Keras 2 기준임
# 그러나 TensorFlow는 2.16부터 기본값이 Keras 3라서 에러 발생
# 예전 Keras 2를 쓰도록 되돌려야 하며 import deeplabcut보다 반드시 먼저 설정되어야 함
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")


def _patch_tf_keras_legacy_layers() -> None:
    """
    버전 호환 문제:
    tensorflow에 "tf_keras.legacy_tf_layers.normalization 위치에서
    코드를 가져와라"라고 경로가 하드코딩된 다리 역할 코드가 있음
    (resnet 백본이 거치는 tf_slim이 이 다리를 씀)
    근데 실제 tf_keras 패키지는 그 코드를 tf_keras.src.legacy_tf_layers
    라는 다른 위치로 옮겨놓고 옛날 경로는 안 남겨놓은 문제 
    """
    import sys

    import tf_keras.src.legacy_tf_layers as legacy_tf_layers
    import tf_keras.src.legacy_tf_layers.normalization as legacy_normalization

    '''
    해결: 옛날 경로(tf_keras.legacy_tf_layers)로 찾아오면
    진짜 위치(tf_keras.src.legacy_tf_layers)를 대신 돌려주도록 sys.modules에 별칭으로 연결
    '''
    sys.modules.setdefault("tf_keras.legacy_tf_layers", legacy_tf_layers)
    sys.modules.setdefault("tf_keras.legacy_tf_layers.normalization", legacy_normalization)

### 라벨링 CSV ###

def header_rows(scorer: str, joints: list[str]) -> list[list[str]]:
    joint_columns = [joint for joint in joints for _ in range(2)]
    return [
        ["scorer"] + [scorer] * (len(joints) * 2),
        ["bodyparts"] + joint_columns,
        ["coords"] + ["x", "y"] * len(joints),
    ]


def coordinate_rows(video_name: str, frame_names: list[str], bodyparts: np.ndarray) -> list[list[str]]:
    rows = []
    for i, frame_name in enumerate(frame_names):
        coords = [float(v) for v in bodyparts[i]]
        rows.append([f"labeled-data/{video_name}/{frame_name}"] + coords)
    return rows


def save_collected_data(
    filepath: str,
    scorer: str,
    joints: list[str],
    video_path: str,
    frame_names: list[str],
    bodyparts: np.ndarray,
) -> None:
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(header_rows(scorer, joints))
        writer.writerows(coordinate_rows(video_name, frame_names, bodyparts))


### 프레임 추출 ###

DEFAULT_DOTSIZE = 4


def create_labeling_project(task: str, scorer: str, video_path: str, working_directory: str) -> str:
    import deeplabcut.utils.auxiliaryfunctions as auxiliaryfunctions
    import deeplabcut

    # create_new_project는 새로 만든 프로젝트의 config.yaml 경로를 그대로 반환
    config_path = deeplabcut.create_new_project(
        task, scorer, [video_path], working_directory=working_directory, copy_videos=True
    )
    cfg = auxiliaryfunctions.read_config(config_path)
    cfg["dotsize"] = DEFAULT_DOTSIZE
    auxiliaryfunctions.write_config(config_path, cfg)
    return config_path


def frames_subdirectory(project_path: str, video_path: str) -> str:
    project_base = os.path.dirname(project_path)
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    return os.path.join(project_base, "labeled-data", video_name)


def set_bodyparts(config_path: str, joints: list[str]) -> None:
    # DeepLabCut이 자동으로 만드는 config.yaml의 joint명을 나머지 내용은 유지하며 수정하기 위해
    # DeepLabCut 자체의 read/write 함수를 사용해서 joint명 변경

    import deeplabcut.utils.auxiliaryfunctions as auxiliaryfunctions

    cfg = auxiliaryfunctions.read_config(config_path)
    cfg["bodyparts"] = list(joints)
    auxiliaryfunctions.write_config(config_path, cfg)


def extract_frames_for_labeling(
    capture: cv2.VideoCapture,
    video_path: str,
    total_video_frames: int,
    frame_count: int,
    scorer: str,
    task: str = "deepPTA",
    timestamp: datetime | None = None,
    projects_root: str = DEFAULT_PROJECTS_ROOT,
) -> tuple[str, list[str]]:
    # 새 DeepLabCut 프로젝트 생성 및 프레임 추출
    # labeled-data 폴더 경로랑 추출된 프레임 파일명 반환

    import cv2

    timestamp = timestamp or datetime.now()
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    working_directory = os.path.join(projects_root, f"{video_name}_{timestamp:%Y-%m-%d_%H%M%S}")
    os.makedirs(working_directory, exist_ok=True)

    project_path = create_labeling_project(task, scorer, video_path, working_directory)
    labeled_data_dir = frames_subdirectory(project_path, video_path)

    stride = max(1, total_video_frames // frame_count)
    frame_names = []
    lower_bound = 1
    for _ in range(frame_count):
        frame_number = random.randint(lower_bound, lower_bound + stride)
        ok, frame = capture.read()
        if not ok:
            break
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        name = f"img{frame_number:05d}.png"
        cv2.imwrite(os.path.join(labeled_data_dir, name), frame)
        frame_names.append(name)
        lower_bound += stride

    return labeled_data_dir, frame_names


### 학습 / 추론 ###
def train_model(
    config_path: str,
    scorer: str,
    max_snapshots_to_keep: int,
    save_iters: int,
    max_iters: int,
    joints: list[str],
) -> None:
    import deeplabcut

    _patch_tf_keras_legacy_layers()
    if joints:
        set_bodyparts(config_path, joints)
    deeplabcut.convertcsv2h5(config_path, scorer=scorer, userfeedback=False)
    deeplabcut.create_training_dataset(config_path, augmenter_type="imgaug")
    deeplabcut.train_network(
        config_path, max_snapshots_to_keep=max_snapshots_to_keep, saveiters=save_iters, maxiters=max_iters
    )
    deeplabcut.evaluate_network(config_path)


def make_prediction(config_path: str, videos_directory: str = "videos") -> None:
    # videos_directory : DeepLabCut 프로젝트(config_path가 들어있는 폴더) 기준 상대경로
    # 실제로 분석할 영상이 있는 곳은 프로젝트 자체의 'videos/'폴더
    import deeplabcut

    _patch_tf_keras_legacy_layers()
    project_dir = os.path.dirname(config_path)
    video_list = glob.glob(os.path.join(project_dir, videos_directory, "*.mp4"))
    deeplabcut.analyze_videos(config_path, video_list, dynamic=(True, 0.5, 10))
    
    # filterpredictions->create_labeled_video->plot_trajectories
    deeplabcut.filterpredictions(config_path, video_list)
    deeplabcut.create_labeled_video(config_path, video_list, filtered=True)
    deeplabcut.plot_trajectories(config_path, video_list, filtered=True)
