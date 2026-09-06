"""
DeepLabCut prediction csv로 포인트 별 평균 신뢰도 계산한 뒤 GUI에 띄우는 코드
"""
from __future__ import annotations

import matplotlib.cm as cm
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

#config.yaml의 colormap 설정 맞추기 
DLC_COLORMAP = "rainbow"

#각 포인트별 평균 신뢰도 계산
def compute_mean_likelihood(df: pd.DataFrame) -> pd.Series:
    """``df`` must have a 3-level column header (scorer, bodyparts, coords),
    i.e. read with ``pd.read_csv(path, header=[0, 1, 2], index_col=0)``."""
    likelihood = df.xs("likelihood", axis=1, level=-1)
    likelihood.columns = likelihood.columns.get_level_values("bodyparts")
    return likelihood.astype(float).mean()

#csv 읽어서 전달
def load_mean_likelihood(csv_path: str) -> pd.Series:
    df = pd.read_csv(csv_path, header=[0, 1, 2], index_col=0)
    return compute_mean_likelihood(df)

#matplotlib로 그래프 그리기
class LikelihoodChartWidget(FigureCanvasQTAgg):
    """Bar chart of mean per-bodypart label confidence, embedded in the GUI."""
    #캔버스 연결
    def __init__(self, parent=None):
        self.figure = Figure(figsize=(6, 4))
        super().__init__(self.figure)
        if parent is not None:
            self.setParent(parent)
    #그래프 그리기
    def plot_csv(self, csv_path: str) -> None:
        mean_likelihood = load_mean_likelihood(csv_path)
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        colormap = cm.get_cmap(DLC_COLORMAP)
        colors = colormap(np.linspace(0, 1, len(mean_likelihood)))
        bars = ax.bar(mean_likelihood.index, mean_likelihood.values, color=colors)
        ax.set_xlabel("Body Parts")
        ax.set_ylabel("Mean Likelihood")
        ax.set_title("Mean Likelihood of Each Body Part Across Frames")
        ax.set_ylim(0, 1.05)
        for bar, value in zip(bars, mean_likelihood.values):
            ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.4f}", ha="center", va="bottom")
        self.figure.tight_layout()
        self.draw()
