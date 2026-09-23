# SPDX-License-Identifier: GPL-3.0-or-later
"""设备工作台：搜索筛选、房间分组与设备即时状态。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)
import qtawesome as qta

from app.core import icon_store
from app.core.models import DeviceInfo
from app.ui.si_theme import SiColors
from app.ui.shell.home_models import classify_device, group_rooms


_KINDS = ("全部", "灯光", "空调", "窗帘", "影音", "传感器", "其他")
_KIND_NAME = {"light": "灯光", "climate": "空调", "curtain": "窗帘",
              "media": "影音", "sensor": "传感器", "other": "其他"}
_KIND_ICON = {"light": "mdi.lightbulb-outline", "climate": "mdi.snowflake",
              "curtain": "mdi.blinds", "media": "mdi.television",
              "sensor": "mdi.motion-sensor", "other": "mdi.devices"}


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear(item.layout())


def _label(value: str, size=10, muted=False) -> QLabel:
    label = QLabel(value)
    label.setWordWrap(True)
    label.setFont(QFont("Microsoft YaHei UI", size,
                        QFont.Weight.Normal if muted else QFont.Weight.DemiBold))
    label.setStyleSheet(f"color: {SiColors.TEXT_MUTED if muted else SiColors.TEXT_PRIMARY};")
    return label


class DevicesPage(QWidget):
    device_selected = Signal(str)
    power_toggled = Signal(str)
    open_detail_requested = Signal(str)
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("shellRoot")
        self._devices: list[DeviceInfo] = []
        self._known_power: dict[str, bool | None] = {}
        self._metrics: dict[str, str | None] = {}
        self._selected_id: str | None = None
        self._kind = "全部"
        self._columns = 3
        root = QHBoxLayout(self)
        root.setContentsMargins(24, 10, 18, 16)
        root.setSpacing(16)
        left_host = QWidget()
        left_host.setObjectName("shellRoot")
        left_layout = QVBoxLayout(left_host)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        tools = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setObjectName("shellSearchField")
        self._search.setPlaceholderText("搜索设备名称或型号")
        self._search.setMinimumHeight(38)
        self._search.textChanged.connect(self._rebuild)
        tools.addWidget(self._search, 1)
        refresh = QPushButton("刷新")
        refresh.setObjectName("shellNeutralButton")
        refresh.clicked.connect(self.refresh_requested.emit)
        tools.addWidget(refresh)
        left_layout.addLayout(tools)
        chip_scroll = QScrollArea()
        chip_scroll.setFrameShape(QFrame.Shape.NoFrame)
        chip_scroll.setFixedHeight(42)
        chip_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        chip_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        chip_host = QWidget()
        chip_host.setObjectName("shellRoot")
        self._chips = QHBoxLayout(chip_host)
        self._chips.setContentsMargins(0, 0, 0, 0)
        chip_scroll.setWidget(chip_host)
        left_layout.addWidget(chip_scroll)
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        host.setObjectName("shellRoot")
        self._list = QVBoxLayout(host)
        self._list.setContentsMargins(0, 0, 0, 0)
        self._list.setSpacing(14)
        scroll.setWidget(host)
        left_layout.addWidget(scroll, 1)
        root.addWidget(left_host, 1)

        right_scroll = QScrollArea()
        self._right_scroll = right_scroll
        right_scroll.setFixedWidth(270)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_host = QWidget()
        right_host.setObjectName("shellRoot")
        self._right = QVBoxLayout(right_host)
        self._right.setContentsMargins(0, 0, 0, 0)
        self._right.setSpacing(12)
        right_scroll.setWidget(right_host)
        root.addWidget(right_scroll)
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

    def update_data(self, devices: list[DeviceInfo],
                    known_power: dict[str, bool | None],
                    metrics: dict[str, str | None]) -> None:
        self._devices = list(devices)
        self._known_power = dict(known_power)
        self._metrics = dict(metrics)
        if self._selected_id not in {d.did for d in self._devices}:
            self._selected_id = self._devices[0].did if self._devices else None
        self._rebuild()

    def select_device(self, did: str) -> None:
        self._selected_id = did
        self.device_selected.emit(did)
        self._rebuild()
        if not self._right_scroll.isVisible():
            self.open_detail_requested.emit(did)

    def _set_kind(self, kind: str) -> None:
        self._kind = kind
        self._rebuild()

    def _rebuild(self) -> None:
        _clear(self._chips)
        _clear(self._list)
        _clear(self._right)
        for kind in _KINDS:
            count = len(self._devices) if kind == "全部" else sum(
                _KIND_NAME[classify_device(d)] == kind for d in self._devices)
            button = QPushButton(f"{kind} {count}")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            selected = kind == self._kind
            button.setStyleSheet(
                f"QPushButton {{ background: {SiColors.THEME if selected else SiColors.CARD};"
                f" color: {SiColors.ON_THEME_TEXT if selected else SiColors.TEXT_PRIMARY};"
                " border: none; border-radius: 13px; padding: 6px 10px; }}")
            button.clicked.connect(lambda _=False, k=kind: self._set_kind(k))
            self._chips.addWidget(button)
        self._chips.addStretch()
        self._chips.parentWidget().adjustSize()

        query = self._search.text().strip().casefold()
        filtered = [d for d in self._devices
                    if (not query or query in d.name.casefold() or query in d.model.casefold())
                    and (self._kind == "全部" or _KIND_NAME[classify_device(d)] == self._kind)]
        if filtered:
            for room in group_rooms(filtered):
                self._list.addWidget(_label(f"{room.name}  ·  {len(room.devices)} 台设备", 12))
                host = QWidget()
                grid = QGridLayout(host)
                grid.setContentsMargins(0, 0, 0, 0)
                grid.setSpacing(10)
                for i, device in enumerate(room.devices):
                    grid.addWidget(self._card(device), i // self._columns, i % self._columns)
                self._list.addWidget(host)
        else:
            empty = QFrame()
            empty.setObjectName("homeSectionCard")
            empty.setMinimumHeight(210)
            lay = QVBoxLayout(empty)
            lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            line = _label("暂无匹配设备", 11)
            line.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(line)
            lay.addWidget(_label("请调整搜索或筛选条件，或刷新设备列表。", 9, True))
            self._list.addWidget(empty)
        self._list.addStretch()
        selected = next((d for d in self._devices if d.did == self._selected_id), None)
        self._right.addWidget(self._detail(selected))
        self._right.addStretch()

    def _device_icon(self, device: DeviceInfo, size: int) -> QLabel:
        icon = QLabel()
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(size, size)
        path = icon_store.icon_path(device.model)
        pix = QPixmap(str(path)) if path.is_file() else QPixmap()
        if pix.isNull():
            icon.setPixmap(qta.icon(_KIND_ICON[classify_device(device)],
                                     color=SiColors.THEME).pixmap(size - 10, size - 10))
        else:
            icon.setPixmap(pix.scaled(size - 6, size - 6,
                                       Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation))
        return icon

    def _card(self, device: DeviceInfo) -> QWidget:
        card = QFrame()
        card.setObjectName("homeSectionCard")
        card.setMinimumHeight(112)
        if device.did == self._selected_id:
            card.setStyleSheet(f"QFrame#homeSectionCard {{ border: 2px solid {SiColors.THEME};"
                               " border-radius: 15px; }}")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(7)
        row = QHBoxLayout()
        row.addWidget(self._device_icon(device, 44))
        row.addStretch()
        state = self._known_power.get(device.did)
        if device.online and state is not None:
            power = QPushButton()
            power.setFixedSize(30, 30)
            power.setIcon(qta.icon("mdi.power", color=SiColors.ON_THEME_TEXT if state else SiColors.TEXT_SECONDARY))
            power.setStyleSheet(f"background: {SiColors.THEME if state else SiColors.SURFACE};"
                                " border: none; border-radius: 15px;")
            power.clicked.connect(lambda: self.power_toggled.emit(device.did))
            row.addWidget(power)
        lay.addLayout(row)
        select = QPushButton(device.name)
        select.setCursor(Qt.CursorShape.PointingHandCursor)
        select.setStyleSheet(f"color: {SiColors.TEXT_PRIMARY}; background: transparent;"
                             " border: none; text-align: left; font-weight: 600;")
        select.clicked.connect(lambda: self.select_device(device.did))
        lay.addWidget(select)
        status = "离线" if not device.online else (
            "已开启" if state is True else "已关闭" if state is False else "在线")
        lay.addWidget(_label(status, 9, True))
        metric = self._metrics.get(device.did)
        if metric and device.online:
            lay.addWidget(_label(metric, 8, True))
        return card

    def _detail(self, device: DeviceInfo | None) -> QWidget:
        card = QFrame()
        card.setObjectName("homeSectionCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 18, 16, 18)
        lay.setSpacing(12)
        lay.addWidget(_label("设备详情", 13))
        if device is None:
            lay.addWidget(_label("选择一台设备查看状态。", 9, True))
            return card
        lay.addWidget(self._device_icon(device, 80))
        lay.addWidget(_label(device.name, 14))
        kind = _KIND_NAME[classify_device(device)]
        for name, value in (("房间", device.room_name or "未分配"),
                            ("类型", kind), ("状态", "在线" if device.online else "离线"),
                            ("型号", device.model)):
            lay.addWidget(_label(name, 9, True))
            lay.addWidget(_label(value, 9))
        metric = self._metrics.get(device.did)
        if metric and device.online:
            lay.addWidget(_label("即时读数", 9, True))
            lay.addWidget(_label(metric, 10))
        state = self._known_power.get(device.did)
        if device.online and state is not None:
            power = QPushButton("关闭设备" if state else "开启设备")
            power.setObjectName("shellNeutralButton")
            power.setMinimumHeight(36)
            power.clicked.connect(lambda: self.power_toggled.emit(device.did))
            lay.addWidget(power)
        detail = QPushButton("更多控制与属性")
        detail.setObjectName("shellNeutralButton")
        detail.setMinimumHeight(36)
        detail.clicked.connect(lambda: self.open_detail_requested.emit(device.did))
        lay.addWidget(detail)
        lay.addWidget(_label("设备支持的其他控制，以详情面板实际返回为准。", 9, True))
        return card
