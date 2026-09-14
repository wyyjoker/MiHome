# SPDX-License-Identifier: GPL-3.0-or-later
# MiHome-Windows: 米家设备的 Windows 桌面控制端
"""场景页：列出米家手动场景并一键执行。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import qtawesome as qta

from app.core.models import SceneInfo
from app.ui.si_theme import SiColors


class ScenesPage(QScrollArea):
    """手动场景列表。加载与执行由 MainWindow 经 JobExecutor 完成。"""

    run_requested = Signal(str, str)  # scene_id, home_id
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._host = QWidget()
        self._host.setObjectName("shellRoot")
        self._root = QVBoxLayout(self._host)
        self._root.setContentsMargins(32, 20, 32, 24)
        self._root.setSpacing(14)
        self.setWidget(self._host)

        self._scenes: list[SceneInfo] = []
        self._busy_ids: set[str] = set()
        self._rebuild()

    def set_scenes(self, scenes: list[SceneInfo]) -> None:
        self._scenes = list(scenes)
        self._rebuild()

    def set_busy(self, scene_id: str, busy: bool) -> None:
        if busy:
            self._busy_ids.add(scene_id)
        else:
            self._busy_ids.discard(scene_id)
        self._rebuild()

    def _clear(self) -> None:
        while self._root.count():
            item = self._root.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _rebuild(self) -> None:
        self._clear()

        header = QHBoxLayout()
        title = QLabel("场景")
        title.setFont(QFont("Microsoft YaHei UI", 20, QFont.Weight.DemiBold))
        title.setStyleSheet(
            f"color: {SiColors.TEXT_PRIMARY}; background: transparent;")
        header.addWidget(title)
        header.addStretch(1)
        if self._scenes:
            count = QLabel(f"{len(self._scenes)} 个手动场景")
            count.setStyleSheet(
                f"color: {SiColors.TEXT_SECONDARY}; background: transparent;")
            header.addWidget(count)
            header.addSpacing(12)
        refresh = QPushButton()
        refresh.setFixedSize(38, 38)
        refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh.setIcon(qta.icon("mdi.refresh", color=SiColors.TEXT_SECONDARY))
        refresh.setStyleSheet(
            f"QPushButton {{ background: {SiColors.CARD}; border: 1px solid {SiColors.LINE};"
            f" border-radius: 12px; }}"
            f"QPushButton:hover {{ background: {SiColors.CARD_HOVER}; }}")
        refresh.clicked.connect(self.refresh_requested.emit)
        header.addWidget(refresh)
        host = QWidget()
        host.setLayout(header)
        self._root.addWidget(host)

        if not self._scenes:
            empty = QLabel("暂无手动场景\n可在米家 App「智能 → 手动场景」中创建后点刷新")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(
                f"color: {SiColors.TEXT_SECONDARY}; background: transparent;"
                f" font-size: 11pt;")
            empty.setWordWrap(True)
            wrap = QWidget()
            wl = QVBoxLayout(wrap)
            wl.addStretch(1)
            wl.addWidget(empty)
            wl.addStretch(1)
            wrap.setMinimumHeight(280)
            self._root.addWidget(wrap)
            return

        for scene in self._scenes:
            self._root.addWidget(self._scene_row(scene))
        self._root.addStretch(1)

    def _scene_row(self, scene: SceneInfo) -> QWidget:
        card = QFrame()
        card.setObjectName("commonDeviceCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(12)

        badge = QFrame()
        badge.setFixedSize(40, 40)
        badge.setStyleSheet(
            f"QFrame {{ background: {SiColors.SURFACE}; border-radius: 12px; }}")
        bl = QVBoxLayout(badge)
        bl.setContentsMargins(0, 0, 0, 0)
        ic = QLabel()
        ic.setPixmap(qta.icon("mdi.play-circle-outline", color=SiColors.THEME).pixmap(20, 20))
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(ic)
        lay.addWidget(badge)

        col = QVBoxLayout()
        col.setSpacing(2)
        name = QLabel(scene.name)
        name.setStyleSheet(
            f"color: {SiColors.TEXT_PRIMARY}; background: transparent;"
            f" font-size: 11pt; font-weight: 600;")
        sub = QLabel(scene.home_name or "手动场景")
        sub.setStyleSheet(
            f"color: {SiColors.TEXT_MUTED}; background: transparent; font-size: 9pt;")
        col.addWidget(name)
        col.addWidget(sub)
        lay.addLayout(col, 1)

        busy = scene.scene_id in self._busy_ids
        btn = QPushButton("执行中…" if busy else "执行")
        btn.setFixedSize(72, 32)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setEnabled(not busy)
        btn.setStyleSheet(
            f"QPushButton {{ background: {SiColors.THEME}; border: none; border-radius: 10px;"
            f" color: {SiColors.ON_THEME_TEXT}; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {SiColors.THEME_HOVER}; }}"
            f"QPushButton:disabled {{ background: {SiColors.STATE_OFF}; color: {SiColors.TEXT_MUTED}; }}")
        btn.clicked.connect(
            lambda: self.run_requested.emit(scene.scene_id, scene.home_id))
        lay.addWidget(btn)
        return card
