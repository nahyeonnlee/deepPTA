# DeepPTA

자세 추정(pose estimation) 기술은 대상의 자세를 인식하고 분석하는 데 중요한 역할을 합니다. 이 기술은 스포츠, 의학, 엔터테인먼트, 로봇공학 등 여러 분야에서 광범위하게 활용되고 있으나 이를 활용하기 위해서는 고도의 프로그래밍 기술과 복잡한 알고리즘 이해가 필요하기 때문에, 많은 사용자들이 쉽게 접근하기 어려운 것이 현실입니다.

이 프로젝트는 동물 행동 실험용 자세 추정 파이프라인으로, 비개발자도 손쉽고 빠르게 pose estimation 작업을 수행할 수 있도록 설계한 캡스톤 프로젝트(2024)이며, 한양대학교 캡스톤디자인 발표회에서 장려상을 받았습니다.

동물 행동 실험 영상을 DeepLabCut 학습용 프로젝트로 자동 변환해주는 PyQt5 기반 데스크톱 앱입니다. 영상 불러오기, 프레임 추출, 라벨링, 학습·추론에 이르는 전 과정을 GUI 안에서 처리할 수 있어, DeepLabCut 프로젝트 파일을 직접 다룰 필요가 없습니다.

이 프로젝트는 DeepLabCut(AGPL-3.0)을 의존성으로 사용하며, DeepLabCut 자체는 이 저장소에 포함되어 있지 않습니다.


## 워크플로우

```
영상 추가 → 프레임 샘플 추출 → 조인트 이름 설정 → 프레임마다 클릭 라벨링
    → CollectedData CSV 저장 → DeepLabCut 모델 학습 → 예측 결과 분석
```

## 폴더 구조

```
code/
├── __init__.py
├── __main__.py
├── main_window.py
├── state.py
├── video_player.py
├── labeling_controller.py
├── geometry.py
├── dialogs.py
├── dlc.py
└── analysis.py
ui/            # Qt Designer .ui 파일들
assets/icons/  # 재생 버튼 아이콘
```

## 설치 방법

```bash
conda create -n deepPTA python=3.9
conda activate deepPTA
./install.sh
```

### 설명
1. `deepPTA`라는 이름의 conda 환경(Python 3.9, Apple Silicon에서 DeepLabCut 2.3.x가
필요로 하는 버전)에서 실행

2. `install.sh`가 DeepLabCut의 tables 버전 고정 문제(Apple Silicon용 wheel 없음) conda 설치 + `--no-deps`로 우회

3. tf-keras로 Keras 버전 호환 처리


## 실행

```bash
python -m code
```

## 한계점 및 향후 추가 내용

- 프레임 추출은 아직 한 번에 영상 하나만 라벨링한다고 가정함
- 학습/추론 호출 중에 진행 상황 표시 추가
