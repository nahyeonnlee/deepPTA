# deepPTA

> 동물 행동 실험용 자세 추정(pose estimation) 데스크톱 앱  
> 🏆 한양대학교 바이오메디컬공학부 캡스톤디자인 발표회 장려상 (2024)

자세 추정 기술은 스포츠·의학·로봇공학 등 여러 분야에서 쓰이지만, 활용하려면 프로그래밍 기술과 복잡한 알고리즘 이해가 필요해 많은 사용자가 쉽게 접근하기 어렵습니다. DeepLabCut도 GUI를 제공하지만, 설치·실행과 오류 확인은 터미널에서, 일부 설정은 `config.yaml`을 직접 수정해야 합니다.

deepPTA는 **설치 이후에는 코드나 터미널 없이** 영상 추가부터 라벨링·학습·분석까지 **전 과정을 하나의 GUI에서 처리**할 수 있도록 만든 PyQt5 기반 데스크톱 앱입니다. DeepLabCut 프로젝트 파일을 직접 다룰 필요가 없습니다.

> 이 프로젝트는 DeepLabCut(AGPL-3.0)을 의존성으로 사용하며, DeepLabCut 자체는 이 저장소에 포함되어 있지 않습니다.

**Tech Stack** · Python · PyQt5 · DeepLabCut · OpenCV

## 워크플로우

```
영상 추가 → 프레임 샘플 추출 → 조인트 이름 설정 → 프레임마다 클릭 라벨링
    → CollectedData CSV 저장 → DeepLabCut 모델 학습 → 예측 결과 분석
```

## 주요 기능

### 메인 화면 · 비디오 추가 및 처리

<p align="center">
  <img src="assets/screenshots/main.png" width="600" alt="deepPTA 메인 화면">
</p>

- 분석할 영상을 추가하고 목록에서 프레임 수·FPS를 확인
- 영상 재생 컨트롤로 구간을 살펴보며 다음 단계로 진행

### 1. 프레임 추출 · 라벨 옵션 설정

<p align="center">
  <img src="assets/screenshots/label_option.png" width="600" alt="프레임 추출 및 라벨 옵션 설정">
</p>

- 추출할 프레임 수를 입력하면 전체 구간에서 균등하게 추출
- 관절 포인트의 개수와 이름을 창에서 바로 지정

### 2. 프레임 라벨링

<p align="center">
  <img src="assets/screenshots/labeling.png" width="600" alt="프레임 라벨링">
</p>

- 프레임을 클릭해 관절 좌표를 라벨링, 라벨 삭제·재설정 지원
- 라벨 좌표를 저장하고 학습 데이터로 변환

### 3. 모델 학습 · 결과 분석

<p align="center">
  <img src="assets/screenshots/analysis.png" width="600" alt="모델 학습 및 결과 분석">
</p>

- 학습 파라미터를 입력해 학습을 실행하고 새 영상에 포즈 추정
- 관절 포인트별 평균 신뢰도(likelihood) 그래프와 결과 영상 표시
- 학습 조건: ResNet-50 · 10,000 iterations · 라벨 프레임 20장

## 폴더 구조

```
code/
├── __init__.py
├── __main__.py              # 실행 진입점 (python -m code)
├── main_window.py           # UI: 위젯과 핸들러 연결만 담당
├── state.py                 # 상태: ProjectState 데이터클래스 하나를 모든 창이 공유
├── video_player.py          # 로직: 영상 재생
├── labeling_controller.py   # 로직: 라벨링 컨트롤러
├── geometry.py              # 로직: 좌표 변환
├── dialogs.py               # 라벨 옵션 등 보조 창
├── dlc.py                   # 연동: DeepLabCut 호출·호환 패치
└── analysis.py              # 연동: 신뢰도 그래프
ui/                          # Qt Designer .ui 파일들
assets/icons/                # 재생 버튼 아이콘
assets/screenshots/          # README용 스크린샷
```

## 설치 방법

```bash
conda create -n deepPTA python=3.9
conda activate deepPTA
./install.sh
```

Apple Silicon에서 DeepLabCut 2.3.x가 필요로 하는 Python 3.9 환경을 기준으로 합니다.

## 실행

```bash
python -m code
```
