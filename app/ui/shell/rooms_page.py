# SPDX-License-Identifier: GPL-3.0-or-later
"""房间总览：房间切换、设备分组与实时状态。"""

from __future__ import annotations

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

import qtawesome as qta

from app import resource_path
from app.core import icon_store
from app.core.models import DeviceInfo
from app.ui.si_theme import SiColors
from app.ui.shell.home_models import classify_device, group_rooms


_ROOM_IMAGE = {
    "客厅": "room-photo-living.png",
    "主卧": "room-photo-bedroom.png",
    "次卧": "room-photo-bedroom.png",
    "书房": "room-photo-study.png",
}

_CATEGORY = {
    "light": ("灯光", "mdi.lightbulb-outline"),
    "climate": ("空调与气候", "mdi.snowflake"),
    "curtain": ("窗帘", "mdi.blinds"),
    "media": ("影音", "mdi.television"),
    "sensor": ("传感器", "mdi.motion-sensor"),
    "other": ("其他设备", "mdi.devices"),
}


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().deleteLater()
        elif item.layout() is not None:
            _clear(item.layout())


def _metric_pair(devices: list[DeviceInfo], metrics: dict[str, str | None]) -> tuple[str, str]:
    """仅从已回读的设备指标取温湿度，缺失时不制造数字。"""
    temp, humidity = "暂无读数", "暂无读数"
    for device in devices:
        if not device.online:
            continue
        value = metrics.get(device.did) or ""
        if temp == "暂无读数":
            found = re.search(r"(-?\d+(?:\.\d+)?)\s*°C", value)
            if found:
                temp = f"{float(found.group(1)):g}°C"
        if humidity == "暂无读数":
            found = re.search(r"(\d+(?:\.\d+)?)\s*%", value)
            if found:
                humidity = f"{float(found.group(1)):g}%"
    return temp, humidity


class _RoomHero(QWidget):
    def __init__(self, room: str, total: int, online: int, parent=None):
        super().__init__(parent)
        self._room = room
        self._total = total
        self._online = online
        self.setFixedHeight(184)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        filename = _ROOM_IMAGE.get(room, "room-photo-living.png")
        self._pix = QPixmap(str(resource_path(f"app/ui/shell/assets/{filename}")))

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(SiColors.CARD))
        painter.drawRoundedRect(self.rect(), 18, 18)
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 18, 18)
        painter.setClipPath(path)
        if not self._pix.isNull():
            scaled = self._pix.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap((self.width() - scaled.width()) // 2,
                               (self.height() - scaled.height()) // 2, scaled)
        shade = QLinearGradient(0, 0, 0, self.height())
        shade.setColorAt(0, QColor(20, 20, 20, 12))
        shade.setColorAt(1, QColor(25, 24, 22, 160))
        painter.fillRect(self.rect(), shade)
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Microsoft YaHei UI", 22, QFont.Weight.Bold))
        painter.drawText(24, self.height() - 78, self._room)
        painter.setFont(QFont("Microsoft YaHei UI", 10))
        painter.drawText(25, self.height() - 47,
                         f"{self._total} 台设备 · {self._online} 台在线")
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.drawText(25, self.height() - 22, "智能让家更温暖")


class _RoomPickerButton(QPushButton):
    def __init__(self, room: str, count: int, selected: bool, parent=None):
        super().__init__(parent)
        self._room = room
        self._count = count
        self._selected = selected
        filename = _ROOM_IMAGE.get(room, "room-photo-living.png")
        self._pix = QPixmap(str(resource_path(f"app/ui/shell/assets/{filename}")))
        self.setFixedSize(150, 72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event) -> None:  # noqa: N802
        from PySide6.QtGui import QPainterPath, QPen
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().adjusted(1, 1, -1, -1), 13, 13)
        painter.setClipPath(path)
        if self._pix.isNull():
            painter.fillRect(self.rect(), QColor(SiColors.CARD))
        else:
            scaled = self._pix.scaled(self.size(),
                                      Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                      Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap((self.width() - scaled.width()) // 2,
                               (self.height() - scaled.height()) // 2, scaled)
        painter.fillRect(self.rect(), QColor(20, 22, 22, 115))
        painter.setClipping(False)
        painter.setPen(QPen(QColor(SiColors.THEME if self._selected else SiColors.CHIP_BORDER),
                            2 if self._selected else 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 13, 13)
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.DemiBold))
        painter.drawText(12, 30, self._room)
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        painter.drawText(12, 51, f"{self._count} 台设备")


class RoomsPage(QWidget):
    room_selected = Signal(str)
    device_selected = Signal(str)
    power_toggled = Signal(str)
    power_many_requested = Signal(list, bool)
    open_scenes_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("shellRoot")
        self._devices: list[DeviceInfo] = []
        self._known_power: dict[str, bool | None] = {}
        self._metrics: dict[str, str | None] = {}
        self._selected_room: str | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(24, 8, 18, 16)
        root.setSpacing(16)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._left_host = QWidget()
        self._left_host.setObjectName("shellRoot")
        self._left_layout = QVBoxLayout(self._left_host)
        self._left_layout.setContentsMargins(0, 0, 0, 0)
        self._left_layout.setSpacing(14)
        left_scroll.setWidget(self._left_host)
        root.addWidget(left_scroll, 1)

        right_scroll = QScrollArea()
        self._right_scroll = right_scroll
        right_scroll.setFixedWidth(268)
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._right_host = QWidget()
        self._right_host.setObjectName("shellRoot")
        self._right_layout = QVBoxLayout(self._right_host)
        self._right_layout.setContentsMargins(0, 0, 0, 0)
        self._right_layout.setSpacing(12)
        right_scroll.setWidget(self._right_host)
        root.addWidget(right_scroll)
        self._rebuild()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_right_scroll"):
            self._right_scroll.setVisible(self.width() >= 850)

    def update_data(
        self, devices: list[DeviceInfo],
        known_power: dict[str, bool | None] | None = None,
        metrics: dict[str, str | None] | None = None,
    ) -> None:
        self._devices = list(devices)
        self._known_power = dict(known_power or {})
        self._metrics = dict(metrics or {})
        names = [r.name for r in group_rooms(self._devices)]
        if self._selected_room not in names:
            self._selected_room = "客厅" if "客厅" in names else (names[0] if names else None)
        self._rebuild()

    def select_room(self, name: str) -> None:
        if name != self._selected_room:
            self._selected_room = name
            self._rebuild()
        self.room_selected.emit(name)

    def _rebuild(self) -> None:
        _clear(self._left_layout)
        _clear(self._right_layout)
        rooms = group_rooms(self._devices)
        if not rooms:
            empty = QLabel("暂无房间数据\n刷新设备列表后，这里会显示各房间状态。")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {SiColors.TEXT_SECONDARY};")
            self._left_layout.addWidget(empty)
            self._left_layout.addStretch(1)
            self._right_layout.addStretch(1)
            return

        self._left_layout.addWidget(self._room_picker(rooms))
        selected = next((r for r in rooms if r.name == self._selected_room), rooms[0])
        devices = selected.devices
        self._left_layout.addWidget(_RoomHero(selected.name, len(devices), selected.online))

        heading = QLabel(f"{selected.name}设备  ·  {selected.online} 台在线")
        heading.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.DemiBold))
        heading.setStyleSheet(f"color: {SiColors.TEXT_PRIMARY};")
        self._left_layout.addWidget(heading)

        groups: dict[str, list[DeviceInfo]] = {}
        for device in devices:
            groups.setdefault(classify_device(device), []).append(device)
        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        for index, kind in enumerate(k for k in _CATEGORY if k in groups):
            grid.addWidget(self._category_card(kind, groups[kind]), index // 2, index % 2)
        self._left_layout.addWidget(grid_host)
        self._left_layout.addStretch(1)

        self._right_layout.addWidget(self._status_card(selected.name, devices))
        self._right_layout.addWidget(self._actions_card(devices))
        self._right_layout.addWidget(self._trend_card())
        self._right_layout.addStretch(1)

    def _room_picker(self, rooms) -> QWidget:
        scroll = QScrollArea()
        scroll.setFixedHeight(88)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        host = QWidget()
        host.setObjectName("shellRoot")
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 2)
        row.setSpacing(8)
        for room in rooms:
            button = _RoomPickerButton(
                room.name, len(room.devices), room.name == self._selected_room)
            button.clicked.connect(lambda _=False, name=room.name: self.select_room(name))
            row.addWidget(button)
        row.addStretch(1)
        scroll.setWidget(host)
        return scroll

    def _category_card(self, kind: str, devices: list[DeviceInfo]) -> QWidget:
        title, icon = _CATEGORY[kind]
        card = QFrame()
        card.setObjectName("homeSectionCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(9)
        head = QHBoxLayout()
        symbol = QLabel()
        symbol.setPixmap(qta.icon(icon, color=SiColors.THEME).pixmap(21, 21))
        head.addWidget(symbol)
        label = QLabel(f"{title}  {len(devices)}")
        label.setFont(QFont("Microsoft YaHei UI", 11, QFont.Weight.DemiBold))
        label.setStyleSheet(f"color: {SiColors.TEXT_PRIMARY};")
        head.addWidget(label)
        head.addStretch(1)
        if kind == "light":
            dids = [d.did for d in devices if d.online and self._known_power.get(d.did) is not None]
            if dids:
                bulk = QPushButton("全开 / 全关")
                bulk.setCursor(Qt.CursorShape.PointingHandCursor)
                bulk.setStyleSheet(f"color: {SiColors.THEME}; border: none; background: transparent;")
                bulk.clicked.connect(lambda: self.power_many_requested.emit(
                    dids, not any(self._known_power.get(did) is True for did in dids)))
                head.addWidget(bulk)
        layout.addLayout(head)
        for device in devices[:6]:
            layout.addWidget(self._device_row(device, kind))
        if len(devices) > 6:
            more = QLabel(f"另有 {len(devices) - 6} 台设备，可在设备页查看")
            more.setStyleSheet(f"color: {SiColors.TEXT_MUTED};")
            layout.addWidget(more)
        return card

    def _device_row(self, device: DeviceInfo, kind: str) -> QWidget:
        row = QFrame()
        row.setObjectName("roomDeviceRow")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)
        icon_label = QLabel()
        path = icon_store.icon_path(device.model)
        pix = QPixmap(str(path)) if path.is_file() else QPixmap()
        if pix.isNull():
            icon_label.setPixmap(qta.icon(_CATEGORY[kind][1], color=SiColors.THEME).pixmap(25, 25))
        else:
            icon_label.setPixmap(pix.scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))
        icon_label.setFixedWidth(34)
        lay.addWidget(icon_label)
        col = QVBoxLayout()
        col.setSpacing(1)
        name = QPushButton(device.name)
        name.setCursor(Qt.CursorShape.PointingHandCursor)
        name.setStyleSheet(
            f"QPushButton {{ color: {SiColors.TEXT_PRIMARY}; border: none;"
            " background: transparent; text-align: left; font-weight: 600; }}")
        name.clicked.connect(lambda: self.device_selected.emit(device.did))
        col.addWidget(name)
        state = self._known_power.get(device.did)
        status = "离线" if not device.online else (
            "已开启" if state is True else "已关闭" if state is False else "在线")
        metric = self._metrics.get(device.did)
        sub = QLabel(f"{status} · {metric}" if metric and device.online else status)
        sub.setStyleSheet(f"color: {SiColors.TEXT_MUTED}; font-size: 8pt;")
        col.addWidget(sub)
        lay.addLayout(col, 1)
        if device.online and state is not None:
            power = QPushButton()
            power.setFixedSize(34, 34)
            power.setCursor(Qt.CursorShape.PointingHandCursor)
            power.setIcon(qta.icon("mdi.power", color=SiColors.WHITE if state else SiColors.TEXT_SECONDARY))
            power.setStyleSheet(
                f"QPushButton {{ background: {SiColors.THEME if state else SiColors.SURFACE};"
                " border: none; border-radius: 17px; }}")
            power.clicked.connect(lambda: self.power_toggled.emit(device.did))
            lay.addWidget(power)
        return row

    def _status_card(self, room: str, devices: list[DeviceInfo]) -> QWidget:
        card = self._rail_card()
        lay = card.layout()
        lay.addWidget(self._rail_title(f"{room}状态"))
        temp, humidity = _metric_pair(devices, self._metrics)
        for label, value, icon in (
            ("室内温度", temp, "mdi.thermometer"),
            ("室内湿度", humidity, "mdi.water-percent"),
            ("在线设备", f"{sum(d.online for d in devices)} / {len(devices)}", "mdi.devices"),
        ):
            row = QHBoxLayout()
            ico = QLabel()
            ico.setPixmap(qta.icon(icon, color=SiColors.THEME).pixmap(18, 18))
            row.addWidget(ico)
            text = QLabel(label)
            text.setStyleSheet(f"color: {SiColors.TEXT_SECONDARY};")
            row.addWidget(text, 1)
            value_label = QLabel(value)
            value_label.setStyleSheet(f"color: {SiColors.TEXT_PRIMARY}; font-weight: 600;")
            row.addWidget(value_label)
            lay.addLayout(row)
        return card

    def _actions_card(self, devices: list[DeviceInfo]) -> QWidget:
        card = self._rail_card()
        lay = card.layout()
        lay.addWidget(self._rail_title("快捷操作"))
        lights = [d.did for d in devices if d.online and classify_device(d) == "light"
                  and self._known_power.get(d.did) is not None]
        for text, icon, callback, enabled in (
            ("全开灯光", "mdi.lightbulb-on-outline",
             lambda: self.power_many_requested.emit(lights, True), bool(lights)),
            ("全部关灯", "mdi.lightbulb-off-outline",
             lambda: self.power_many_requested.emit(lights, False), bool(lights)),
            ("查看场景", "mdi.palette-swatch-outline", self.open_scenes_requested.emit, True),
        ):
            button = QPushButton(text)
            button.setIcon(qta.icon(icon, color=SiColors.THEME))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setEnabled(enabled)
            button.setMinimumHeight(37)
            button.setStyleSheet(
                f"QPushButton {{ background: {SiColors.SURFACE};"
                f" color: {SiColors.TEXT_PRIMARY}; border: none;"
                " border-radius: 10px; text-align: left; padding: 7px; }}"
                f"QPushButton:hover {{ background: {SiColors.CARD_HOVER}; }}")
            button.clicked.connect(callback)
            lay.addWidget(button)
        return card

    def _trend_card(self) -> QWidget:
        card = self._rail_card()
        lay = card.layout()
        lay.addWidget(self._rail_title("环境趋势"))
        empty = QLabel("暂无历史环境数据\n当前接口仅提供即时读数")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setWordWrap(True)
        empty.setMinimumHeight(118)
        empty.setStyleSheet(f"color: {SiColors.TEXT_MUTED};")
        lay.addWidget(empty)
        return card

    @staticmethod
    def _rail_card() -> QFrame:
        card = QFrame()
        card.setObjectName("homeSectionCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(11)
        return card

    @staticmethod
    def _rail_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(QFont("Microsoft YaHei UI", 11, QFont.Weight.DemiBold))
        label.setStyleSheet(f"color: {SiColors.TEXT_PRIMARY};")
        return label
