# SPDX-License-Identifier: GPL-3.0-or-later
# MiHome-Windows: 米家设备的 Windows 桌面控制端
"""房间列表页：与首页房间卡同源数据。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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

from app.core.models import DeviceInfo
from app.ui.si_theme import SiColors
from app.ui.shell.home_models import group_rooms


class RoomsPage(QScrollArea):
    room_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._host = QWidget()
        self._lay = QVBoxLayout(self._host)
        self._lay.setContentsMargins(28, 18, 28, 20)
        self._lay.setSpacing(10)
        self._lay.addStretch(1)
        self.setWidget(self._host)

    def update_data(self, devices: list[DeviceInfo]) -> None:
        while self._lay.count():
            item = self._lay.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        title = QLabel("房间")
        title.setStyleSheet(
            f"color: {SiColors.TEXT_PRIMARY}; background: transparent;"
            f" font-size: 18pt; font-weight: 600;")
        self._lay.addWidget(title)
        rooms = group_rooms(devices)
        if not rooms:
            empty = QLabel("暂无房间设备")
            empty.setStyleSheet(f"color: {SiColors.TEXT_SECONDARY}; background: transparent;")
            self._lay.addWidget(empty)
        for room in rooms:
            card = QFrame()
            card.setObjectName("homeSectionCard")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            row = QHBoxLayout(card)
            row.setContentsMargins(16, 14, 16, 14)
            col = QVBoxLayout()
            name = QLabel(room.name)
            name.setStyleSheet(
                f"color: {SiColors.TEXT_PRIMARY}; background: transparent;"
                f" font-size: 12pt; font-weight: 600;")
            sub = QLabel(f"{len(room.devices)} 台设备 · {room.online} 在线")
            sub.setStyleSheet(f"color: {SiColors.TEXT_SECONDARY}; background: transparent;")
            col.addWidget(name)
            col.addWidget(sub)
            row.addLayout(col, 1)
            chevron = QLabel()
            chevron.setPixmap(qta.icon("mdi.chevron-right", color=SiColors.TEXT_MUTED).pixmap(18, 18))
            row.addWidget(chevron)
            room_name = room.name
            card.mousePressEvent = (
                lambda event, n=room_name: self.room_selected.emit(n)
                if event.button() == Qt.MouseButton.LeftButton else None
            )
            self._lay.addWidget(card)
        self._lay.addStretch(1)
