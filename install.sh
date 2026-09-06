#!/usr/bin/env bash
# deepPTA conda 환경을 만들고 activate한 뒤 이 스크립트를 실행하세요.
#
# 문제: pip install deeplabcut을 하면 deeplabcut이 tables==3.8.0을 요구하는데,
# macOS arm64 + Python 3.9 조합용으로 미리 컴파일된 wheel이 없어서 pip이
# 소스 빌드를 시도하다 실패한다.
#
# 해결: 1) tables는 conda로 먼저 설치 (conda-forge가 자체적으로 이미 컴파일해둔
#          버전이 있어서 3.8.0은 아니어도 실제 동작에는 문제없음)
#       2) deeplabcut은 --no-deps로 설치해 tables==3.8.0 요구를 건너뜀
#       3) 나머지 진짜 필요한 의존성은 requirements.txt로 설치
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$CONDA_DEFAULT_ENV" != "deepPTA" ]; then
    echo "경고: conda 환경 'deepPTA'가 활성화되어 있지 않습니다 (현재: ${CONDA_DEFAULT_ENV:-없음})."
    echo "먼저 다음을 실행하세요: conda create -n deepPTA python=3.9 && conda activate deepPTA"
    exit 1
fi

echo "[1/3] tables 설치 (conda-forge)"
conda install -n deepPTA -c conda-forge pytables -y

echo "[2/3] deeplabcut 설치 (--no-deps)"
pip install --no-deps deeplabcut

echo "[3/3] 나머지 의존성 설치"
pip install -r "$SCRIPT_DIR/requirements.txt"

echo "설치 완료"
