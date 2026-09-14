# SPDX-License-Identifier: GPL-3.0-or-later
# MiHome-Windows: 米家设备的 Windows 桌面控制端
"""家庭首页信息流：问候、状态 chips、关注、房间卡、常用设备。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QLinearGradient
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import qtawesome as qta

from app.core.models import DeviceInfo
from app.ui.si_theme import SiColors
from app.ui.shell.home_models import (
    AttentionItem,
    RoomSummary,
    build_attention,
    classify_device,
    greeting_text,
    group_rooms,
    pick_common_devices,
    status_chips,
)

_ROOM_COVER = {
    "客厅": ("#E8D5B5", "#C4A574"),
    "主卧": ("#D5DCE8", "#8FA0B8"),
    "书房": ("#D8E4D8", "#8A9A88"),
    "次卧": ("#E8D8D0", "#B89888"),
    "厨房": ("#E8E0C8", "#B8A878"),
    "阳台": ("#D0E4E8", "#88A8B0"),
    "未分配": ("#E0DDD6", "#A8A298"),
}


class _GradientCover(QWidget):
    def __init__(self, colors: tuple[str, str], height: int = 84, parent=None):
        super().__init__(parent)
        self._colors = colors
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0, QColor(self._colors[0]))
        grad.setColorAt(1, QColor(self._colors[1]))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 12, 12)


class _SectionCard(QFrame):
    def __init__(self, title: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("homeSectionCard")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 14, 16, 14)
        self._layout.setSpacing(10)
        if title:
            t = QLabel(title)
            t.setObjectName("homeSectionTitle")
            t.setFont(QFont("Microsoft YaHei UI", 11, QFont.Weight.DemiBold))
            self._layout.addWidget(t)

    def body(self) -> QVBoxLayout:
        return self._layout


class _Chip(QFrame):
    def __init__(self, icon_key: str, label: str, count: int, parent=None):
        super().__init__(parent)
        self.setObjectName("chipPill")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 12, 6)
        lay.setSpacing(6)
        icons = {
            "light": "mdi.lightbulb-on",
            "climate": "mdi.snowflake",
            "curtain": "mdi.blinds",
            "device": "mdi.devices",
        }
        ic = QLabel()
        ic.setPixmap(qta.icon(
            icons.get(icon_key, "mdi.information-outline"),
            color=SiColors.THEME).pixmap(16, 16))
        lay.addWidget(ic)
        text = QLabel(f"{count} {label}")
        text.setStyleSheet(f"color: {SiColors.TEXT_SECONDARY}; background: transparent;")
        lay.addWidget(text)


class _RoomCard(QFrame):
    clicked = Signal(str)

    def __init__(self, room: RoomSummary, metrics: dict[str, str | None], parent=None):
        super().__init__(parent)
        self.setObjectName("roomCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._room = room.name
        self.setFixedWidth(168)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        cover = _GradientCover(_ROOM_COVER.get(room.name, _ROOM_COVER["未分配"]))
        lay.addWidget(cover)

        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(12, 10, 12, 12)
        body_lay.setSpacing(4)
        title = QLabel(room.name)
        title.setObjectName("roomCardTitle")
        title.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.DemiBold))
        body_lay.addWidget(title)
        sub = QLabel(f"{len(room.devices)} 台 · {room.online} 在线")
        sub.setStyleSheet(f"color: {SiColors.TEXT_SECONDARY}; background: transparent; font-size: 9pt;")
        body_lay.addWidget(sub)
        metric = room.metric_texts(metrics)
        if metric:
            m = QLabel(" · ".join(metric[:2]))
            m.setStyleSheet(f"color: {SiColors.TEXT_MUTED}; background: transparent; font-size: 9pt;")
            body_lay.addWidget(m)
        kinds = []
        for d in room.devices:
            k = classify_device(d)
            if k in ("light", "climate", "curtain") and k not in kinds:
                kinds.append(k)
        if kinds:
            chips = QLabel("  ".join({
                "light": "灯光", "climate": "气候", "curtain": "窗帘"
            }[k] for k in kinds[:3]))
            chips.setStyleSheet(f"color: {SiColors.THEME}; background: transparent; font-size: 9pt;")
            body_lay.addWidget(chips)
        lay.addWidget(body)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._room)
        super().mousePressEvent(event)


class _AttentionRow(QFrame):
    open_device = Signal(str)

    def __init__(self, item: AttentionItem, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(10)
        color = SiColors.WARN_TEXT if item.severity == "battery" else SiColors.TEXT_SECONDARY
        icon_name = "mdi.battery-alert" if item.severity == "battery" else "mdi.wifi-off"
        ic = QLabel()
        ic.setPixmap(qta.icon(icon_name, color=color).pixmap(18, 18))
        lay.addWidget(ic)
        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel(item.title)
        t.setStyleSheet(f"color: {SiColors.TEXT_PRIMARY}; background: transparent;")
        d = QLabel(item.detail)
        d.setStyleSheet(f"color: {SiColors.TEXT_MUTED}; background: transparent; font-size: 9pt;")
        col.addWidget(t)
        col.addWidget(d)
        lay.addLayout(col, 1)
        btn = QPushButton("查看")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; color: {SiColors.THEME}; }}"
            f"QPushButton:hover {{ color: {SiColors.THEME_HOVER}; }}")
        btn.clicked.connect(lambda: self.open_device.emit(item.did))
        lay.addWidget(btn)


class HomePage(QScrollArea):
    """主内容区家庭首页。信号由 MainWindow 接业务。"""

    room_selected = Signal(str)
    device_selected = Signal(str)
    power_toggled = Signal(str)
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._host = QWidget()
        self._host.setObjectName("shellRoot")
        self._root = QVBoxLayout(self._host)
        self._root.setContentsMargins(28, 18, 28, 20)
        self._root.setSpacing(14)
        self.setWidget(self._host)

        self._devices: list[DeviceInfo] = []
        self._known_power: dict[str, bool | None] = {}
        self._metrics: dict[str, str | None] = {}
        self._display_name = "你好"
        self._tray_dids: list[str] = []

    def set_display_name(self, name: str) -> None:
        self._display_name = name or "你好"

    def update_data(
        self,
        devices: list[DeviceInfo],
        known_power: dict[str, bool | None],
        metrics: dict[str, str | None],
        tray_dids: list[str] | None = None,
    ) -> None:
        self._devices = list(devices)
        self._known_power = dict(known_power)
        self._metrics = dict(metrics)
        self._tray_dids = list(tray_dids or [])
        self._rebuild()

    def _clear(self) -> None:
        while self._root.count():
            item = self._root.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            elif item.layout() is not None:
                # 嵌套 layout 的子控件随父 widget 销毁
                pass

    def _rebuild(self) -> None:
        self._clear()
        self._root.addWidget(self._build_header())
        self._root.addWidget(self._build_banner())

        chips = status_chips(self._devices, self._known_power)
        if chips:
            self._root.addWidget(self._build_chips(chips))

        attention = build_attention(self._devices, self._known_power)
        if attention:
            self._root.addWidget(self._build_attention(attention))

        rooms = group_rooms(self._devices)
        if rooms:
            self._root.addWidget(self._build_rooms(rooms))

        common = pick_common_devices(
            self._devices, self._known_power, self._tray_dids)
        if common:
            self._root.addWidget(self._build_common(common))

        self._root.addStretch(1)

    def _build_header(self) -> QWidget:
        row = QHBoxLayout()
        title = QLabel("家庭")
        title.setFont(QFont("Microsoft YaHei UI", 18, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {SiColors.TEXT_PRIMARY}; background: transparent;")
        row.addWidget(title)
        row.addStretch(1)
        refresh = QPushButton()
        refresh.setFixedSize(36, 36)
        refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh.setIcon(qta.icon("mdi.refresh", color=SiColors.TEXT_SECONDARY))
        refresh.setStyleSheet(
            f"QPushButton {{ background: {SiColors.CARD}; border: 1px solid {SiColors.LINE};"
            f" border-radius: 10px; }}"
            f"QPushButton:hover {{ background: {SiColors.CARD_HOVER}; }}")
        refresh.clicked.connect(self.refresh_requested.emit)
        row.addWidget(refresh)
        host = QWidget()
        host.setLayout(row)
        return host

    def _build_banner(self) -> QWidget:
        card = QFrame()
        card.setObjectName("homeSectionCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(22, 20, 22, 20)
        col = QVBoxLayout()
        col.setSpacing(6)
        hello = f"{greeting_text()}，{self._display_name}"
        title = QLabel(hello)
        title.setObjectName("greetingTitle")
        title.setFont(QFont("Microsoft YaHei UI", 18, QFont.Weight.DemiBold))
        col.addWidget(title)
        online = sum(1 for d in self._devices if d.online)
        offline = len(self._devices) - online
        if not self._devices:
            sub_text = "正在同步家庭设备…"
        elif offline:
            sub_text = f"有 {offline} 台设备离线，{online} 台在线"
        else:
            sub_text = f"家里目前一切正常 · {online} 台设备在线"
        sub = QLabel(sub_text)
        sub.setObjectName("greetingSub")
        col.addWidget(sub)
        lay.addLayout(col, 1)
        cover = _GradientCover((SiColors.BANNER_A, SiColors.BANNER_B), height=72)
        cover.setFixedWidth(160)
        lay.addWidget(cover)
        return card

    def _build_chips(self, chips: list[tuple[str, str, int]]) -> QWidget:
        row = QHBoxLayout()
        row.setSpacing(8)
        for key, label, count in chips:
            row.addWidget(_Chip(key, label, count))
        row.addStretch(1)
        host = QWidget()
        host.setLayout(row)
        return host

    def _build_attention(self, items: list[AttentionItem]) -> QWidget:
        card = _SectionCard("需要关注")
        for item in items[:8]:
            row = _AttentionRow(item)
            row.open_device.connect(self.device_selected.emit)
            card.body().addWidget(row)
        return card

    def _build_rooms(self, rooms: list[RoomSummary]) -> QWidget:
        card = _SectionCard("房间")
        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        cols = 3
        for i, room in enumerate(rooms):
            rc = _RoomCard(room, self._metrics)
            rc.clicked.connect(self.room_selected.emit)
            grid.addWidget(rc, i // cols, i % cols)
        card.body().addWidget(grid_host)
        return card

    def _build_common(self, devices: list[DeviceInfo]) -> QWidget:
        card = _SectionCard("常用设备")
        host = QWidget()
        col = QVBoxLayout(host)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(8)
        for d in devices:
            col.addWidget(self._build_common_row(d))
        card.body().addWidget(host)
        return card

    def _build_common_row(self, device: DeviceInfo) -> QWidget:
        row = QFrame()
        row.setObjectName("homeSectionCard")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(12, 10, 12, 10)
        open_btn = QPushButton(f"{device.name}\n{device.room_name or device.home_name}")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; text-align: left;"
            f" color: {SiColors.TEXT_PRIMARY}; }}")
        open_btn.clicked.connect(lambda: self.device_selected.emit(device.did))
        lay.addWidget(open_btn, 1)
        power = QPushButton()
        power.setFixedSize(36, 36)
        power.setCursor(Qt.CursorShape.PointingHandCursor)
        state = self._known_power.get(device.did)
        icon = "mdi.power" if state is not False else "mdi.power-off"
        color = SiColors.THEME if state else SiColors.ICON_DIM
        if state is None:
            color = SiColors.ICON_MUTED
        power.setIcon(qta.icon(icon, color=color))
        power.setStyleSheet(
            f"QPushButton {{ background: {SiColors.SURFACE}; border: none; border-radius: 18px; }}"
            f"QPushButton:hover {{ background: {SiColors.BTN_HOVER}; }}")
        power.clicked.connect(lambda: self.power_toggled.emit(device.did))
        lay.addWidget(power)
        return row
