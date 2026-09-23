# SPDX-License-Identifier: GPL-3.0-or-later
"""手动场景图卡与真实数据详情。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)
import qtawesome as qta

from app import resource_path
from app.core.models import SceneInfo
from app.ui.si_theme import SiColors


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear(item.layout())


def _label(text: str, size: int = 10, muted: bool = False) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setFont(QFont("Microsoft YaHei UI", size,
                        QFont.Weight.Normal if muted else QFont.Weight.DemiBold))
    label.setStyleSheet(f"color: {SiColors.TEXT_MUTED if muted else SiColors.TEXT_PRIMARY};")
    return label


class ScenesPage(QWidget):
    run_requested = Signal(str, str)
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("shellRoot")
        self._scenes: list[SceneInfo] = []
        self._busy_ids: set[str] = set()
        self._selected_id: str | None = None
        self._columns = 3
        root = QHBoxLayout(self)
        root.setContentsMargins(24, 10, 18, 16)
        root.setSpacing(16)
        for width, attr in ((None, "_left"), (270, "_right")):
            scroll = QScrollArea()
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            if width:
                scroll.setFixedWidth(width)
                self._right_scroll = scroll
            host = QWidget()
            host.setObjectName("shellRoot")
            layout = QVBoxLayout(host)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(13)
            setattr(self, attr, layout)
            scroll.setWidget(host)
            root.addWidget(scroll, 1 if width is None else 0)
        self._rebuild()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if not hasattr(self, "_right_scroll"):
            return
        self._right_scroll.setVisible(self.width() >= 850)
        columns = 1 if self.width() < 650 else 2 if self.width() < 1050 else 3
        if columns != self._columns:
            self._columns = columns
            self._rebuild()

    def set_scenes(self, scenes: list[SceneInfo]) -> None:
        self._scenes = list(scenes)
        if self._selected_id not in {s.scene_id for s in self._scenes}:
            self._selected_id = self._scenes[0].scene_id if self._scenes else None
        self._rebuild()

    def set_busy(self, scene_id: str, busy: bool) -> None:
        (self._busy_ids.add if busy else self._busy_ids.discard)(scene_id)
        self._rebuild()

    def retheme(self) -> None:
        self._rebuild()

    def _select(self, scene_id: str) -> None:
        self._selected_id = scene_id
        self._rebuild()

    def _rebuild(self) -> None:
        _clear(self._left)
        _clear(self._right)
        head = QHBoxLayout()
        head.addWidget(_label("手动场景", 15))
        head.addStretch()
        head.addWidget(_label(f"{len(self._scenes)} 个", 9, True))
        refresh = QPushButton("刷新")
        refresh.setObjectName("shellNeutralButton")
        refresh.clicked.connect(self.refresh_requested.emit)
        head.addWidget(refresh)
        self._left.addLayout(head)
        if self._scenes:
            host = QWidget()
            grid = QGridLayout(host)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(12)
            for i, scene in enumerate(self._scenes):
                grid.addWidget(self._card(scene, i), i // self._columns, i % self._columns)
            self._left.addWidget(host)
        else:
            self._left.addWidget(self._empty("暂无手动场景", "在米家 App 创建后刷新。", 230))
        self._left.addWidget(_label("自动化规则", 15))
        self._left.addWidget(self._empty(
            "暂无可展示的自动化规则", "当前接口不提供自动化规则列表。", 130))
        self._left.addStretch()
        scene = next((s for s in self._scenes if s.scene_id == self._selected_id), None)
        self._right.addWidget(self._detail(scene))
        self._right.addStretch()

    def _run_button(self, scene: SceneInfo) -> QPushButton:
        busy = scene.scene_id in self._busy_ids
        button = QPushButton("执行中…" if busy else "执行场景")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setEnabled(not busy)
        button.setMinimumHeight(34)
        button.setStyleSheet(
            f"QPushButton {{ background: {SiColors.THEME}; color: {SiColors.ON_THEME_TEXT};"
            " border: none; border-radius: 10px; font-weight: 600; }"
            f"QPushButton:hover {{ background: {SiColors.THEME_HOVER}; }}")
        button.clicked.connect(lambda: self.run_requested.emit(scene.scene_id, scene.home_id))
        return button

    def _card(self, scene: SceneInfo, index: int) -> QWidget:
        card = QFrame()
        card.setObjectName("homeSectionCard")
        if scene.scene_id == self._selected_id:
            card.setStyleSheet(
                f"QFrame#homeSectionCard {{ border: 2px solid {SiColors.THEME};"
                " border-radius: 16px; }}")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(8, 8, 8, 10)
        lay.setSpacing(7)
        photo = QLabel()
        photo.setMinimumHeight(115)
        photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        photo.setStyleSheet(f"background: {SiColors.SURFACE}; border-radius: 10px;")
        name = ("room-photo-living.png", "room-photo-bedroom.png")[index % 2]
        pix = QPixmap(str(resource_path(f"app/ui/shell/assets/{name}")))
        if not pix.isNull():
            photo.setPixmap(pix.scaled(250, 115, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                       Qt.TransformationMode.SmoothTransformation))
        else:
            photo.setPixmap(qta.icon("mdi.palette-swatch", color=SiColors.THEME).pixmap(40, 40))
        lay.addWidget(photo)
        select = QPushButton(scene.name)
        select.setCursor(Qt.CursorShape.PointingHandCursor)
        select.setStyleSheet(f"color: {SiColors.TEXT_PRIMARY}; background: transparent;"
                             " border: none; text-align: left; font-weight: 600;")
        select.clicked.connect(lambda: self._select(scene.scene_id))
        lay.addWidget(select)
        lay.addWidget(_label(scene.home_name or "手动场景", 8, True))
        lay.addWidget(self._run_button(scene))
        return card

    def _detail(self, scene: SceneInfo | None) -> QWidget:
        card = QFrame()
        card.setObjectName("homeSectionCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 18, 16, 18)
        lay.setSpacing(11)
        lay.addWidget(_label("场景详情", 13))
        if scene is None:
            lay.addWidget(_label("选择一个场景查看详情。", 9, True))
            return card
        lay.addWidget(_label(scene.name, 14))
        if scene.home_name:
            lay.addWidget(_label(f"所属家庭：{scene.home_name}", 9, True))
        lay.addWidget(self._run_button(scene))
        for heading, body in (("场景描述", "当前接口未提供描述"),
                              ("涉及设备", "当前接口未提供关联设备"),
                              ("执行记录", "当前接口未提供执行历史")):
            lay.addWidget(_label(heading))
            lay.addWidget(_label(body, 9, True))
        return card

    @staticmethod
    def _empty(title: str, detail: str, height: int) -> QWidget:
        card = QFrame()
        card.setObjectName("homeSectionCard")
        card.setMinimumHeight(height)
        lay = QVBoxLayout(card)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = QLabel()
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(qta.icon("mdi.palette-swatch-outline", color=SiColors.THEME).pixmap(30, 30))
        lay.addWidget(icon)
        title_label = _label(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title_label)
        sub = _label(detail, 9, True)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)
        return card
