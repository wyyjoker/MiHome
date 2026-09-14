# SPDX-License-Identifier: GPL-3.0-or-later
# MiHome-Windows: 米家设备的 Windows 桌面控制端
"""右侧房间面板：分类设备列表 + 空调深控卡。"""

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

from app.core.models import DeviceDetail, DeviceInfo, PropInfo
from app.ui.si_theme import SiColors
from app.ui.shell.home_models import classify_device

_KIND_META = (
    ("light", "mdi.lightbulb-on-outline", "灯光"),
    ("climate", "mdi.snowflake", "气候"),
    ("curtain", "mdi.blinds", "窗帘"),
    ("media", "mdi.television", "影音"),
    ("sensor", "mdi.motion-sensor", "传感器"),
    ("other", "mdi.dots-horizontal-circle-outline", "其他"),
)


class RoomPanel(QFrame):
    """房间详情侧栏。业务读写由 MainWindow / JobExecutor 承担。"""

    closed = Signal()
    device_selected = Signal(str)
    power_toggled = Signal(str)
    prop_write_requested = Signal(str, str, object)  # did, prop_name, value

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rightPanel")
        self.setFixedWidth(340)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(16, 14, 12, 14)
        self._title = QLabel("房间")
        self._title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Weight.DemiBold))
        self._title.setStyleSheet(
            f"color: {SiColors.TEXT_PRIMARY}; background: transparent;")
        header_lay.addWidget(self._title, 1)
        close = QPushButton()
        close.setFixedSize(32, 32)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setIcon(qta.icon("mdi.close", color=SiColors.TEXT_SECONDARY))
        close.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; border-radius: 8px; }}"
            f"QPushButton:hover {{ background: {SiColors.BTN_HOVER}; }}")
        close.clicked.connect(self._on_close)
        header_lay.addWidget(close)
        root.addWidget(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._body = QWidget()
        self._body_lay = QVBoxLayout(self._body)
        self._body_lay.setContentsMargins(16, 4, 16, 20)
        self._body_lay.setSpacing(12)
        self._body_lay.addStretch(1)
        self._scroll.setWidget(self._body)
        root.addWidget(self._scroll, 1)

        self._devices: list[DeviceInfo] = []
        self._known_power: dict[str, bool | None] = {}
        self._metrics: dict[str, str | None] = {}
        self._room_name = ""
        self._climate_detail: DeviceDetail | None = None
        self._climate_did: str | None = None
        self._climate_values: dict[str, dict] = {}

    def _on_close(self) -> None:
        self.hide()
        self.closed.emit()

    def set_room(
        self,
        room_name: str,
        devices: list[DeviceInfo],
        known_power: dict[str, bool | None],
        metrics: dict[str, str | None],
    ) -> None:
        self._room_name = room_name
        self._devices = list(devices)
        self._known_power = dict(known_power)
        self._metrics = dict(metrics)
        self._title.setText(room_name)
        self._rebuild()
        self.show()
        self.raise_()

    def set_climate_detail(
        self,
        detail: DeviceDetail | None,
        did: str | None,
        values: dict | None = None,
    ) -> None:
        self._climate_detail = detail
        self._climate_did = did
        if did and values is not None:
            self._climate_values[did] = dict(values)
        if self.isVisible():
            self._rebuild()

    def _clear_body(self) -> None:
        while self._body_lay.count():
            item = self._body_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _rebuild(self) -> None:
        self._clear_body()
        groups: dict[str, list[DeviceInfo]] = {}
        for d in self._devices:
            groups.setdefault(classify_device(d), []).append(d)

        for key, icon, label in _KIND_META:
            items = groups.get(key)
            if not items:
                continue
            self._body_lay.addWidget(self._section_header(icon, label, items))
            for d in items:
                self._body_lay.addWidget(self._device_row(d))

        climate = next((d for d in groups.get("climate", []) if d.online), None)
        if climate is not None:
            self._body_lay.addWidget(self._climate_card(climate))

        self._body_lay.addStretch(1)

    def _section_header(self, icon: str, label: str, items: list[DeviceInfo]) -> QWidget:
        row = QHBoxLayout()
        ic = QLabel()
        ic.setPixmap(qta.icon(icon, color=SiColors.THEME).pixmap(18, 18))
        row.addWidget(ic)
        on = sum(1 for d in items if self._known_power.get(d.did) is True)
        text = QLabel(f"{label} · {len(items)} 台")
        text.setStyleSheet(f"color: {SiColors.TEXT_PRIMARY}; background: transparent;")
        row.addWidget(text)
        row.addStretch(1)
        state = QLabel(f"{on} 开" if on else f"{sum(1 for d in items if d.online)} 在线")
        state.setStyleSheet(f"color: {SiColors.TEXT_MUTED}; background: transparent;")
        row.addWidget(state)
        host = QWidget()
        host.setLayout(row)
        return host

    def _device_row(self, device: DeviceInfo) -> QWidget:
        card = QFrame()
        card.setObjectName("homeSectionCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        open_btn = QPushButton(device.name)
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; text-align: left;"
            f" color: {SiColors.TEXT_PRIMARY}; }}")
        open_btn.clicked.connect(lambda: self.device_selected.emit(device.did))
        lay.addWidget(open_btn, 1)
        meta = self._metrics.get(device.did)
        if meta:
            m = QLabel(meta)
            m.setStyleSheet(f"color: {SiColors.TEXT_MUTED}; background: transparent;")
            lay.addWidget(m)
        power = QPushButton()
        power.setFixedSize(32, 32)
        power.setEnabled(device.online)
        power.setCursor(Qt.CursorShape.PointingHandCursor)
        state = self._known_power.get(device.did)
        icon = "mdi.power" if state else "mdi.power-off"
        color = (
            SiColors.THEME if state
            else (SiColors.ICON_DIM if device.online else SiColors.ICON_MUTED)
        )
        power.setIcon(qta.icon(icon, color=color))
        power.setStyleSheet(
            f"QPushButton {{ background: {SiColors.SURFACE}; border: none; border-radius: 16px; }}"
            f"QPushButton:hover {{ background: {SiColors.BTN_HOVER}; }}")
        power.clicked.connect(lambda: self.power_toggled.emit(device.did))
        lay.addWidget(power)
        return card

    def _climate_card(self, device: DeviceInfo) -> QWidget:
        card = QFrame()
        card.setObjectName("homeSectionCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        head = QHBoxLayout()
        name = QLabel(device.name)
        name.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.DemiBold))
        name.setStyleSheet(f"color: {SiColors.TEXT_PRIMARY}; background: transparent;")
        head.addWidget(name, 1)
        running = QLabel("运行中" if self._known_power.get(device.did) else "已关闭")
        running.setStyleSheet(
            f"color: {SiColors.THEME if self._known_power.get(device.did) else SiColors.TEXT_MUTED};"
            f" background: transparent;")
        head.addWidget(running)
        lay.addLayout(head)

        detail = self._climate_detail if self._climate_did == device.did else None
        values = self._climate_values.get(device.did, {})

        def _num(*names: str) -> float | None:
            for n in names:
                if n in values and values[n] is not None:
                    try:
                        return float(values[n])
                    except (TypeError, ValueError):
                        continue
            return None

        target = _num("target-temperature", "target_temperature")
        current = _num("temperature")
        humidity = _num("relative-humidity", "relative_humidity", "humidity")

        temp_row = QHBoxLayout()
        minus = QPushButton("−")
        minus.setFixedSize(40, 40)
        minus.setStyleSheet(self._circle_btn_qss())
        minus.setCursor(Qt.CursorShape.PointingHandCursor)
        plus = QPushButton("+")
        plus.setFixedSize(40, 40)
        plus.setStyleSheet(self._circle_btn_qss())
        plus.setCursor(Qt.CursorShape.PointingHandCursor)
        temp_label = QLabel(f"{target:.0f}°" if target is not None else "--°")
        temp_label.setFont(QFont("Microsoft YaHei UI", 28, QFont.Weight.DemiBold))
        temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        temp_label.setStyleSheet(
            f"color: {SiColors.TEXT_PRIMARY}; background: transparent;")
        temp_row.addWidget(minus)
        temp_row.addWidget(temp_label, 1)
        temp_row.addWidget(plus)
        lay.addLayout(temp_row)

        if current is not None or humidity is not None:
            parts = []
            if current is not None:
                parts.append(f"室内 {current:.0f}°")
            if humidity is not None:
                parts.append(f"湿度 {humidity:.0f}%")
            meta = QLabel("  ".join(parts))
            meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
            meta.setStyleSheet(
                f"color: {SiColors.TEXT_SECONDARY}; background: transparent;")
            lay.addWidget(meta)

        mode_prop = self._find_prop(detail, ("mode", "air-conditioner-mode"))
        if mode_prop is not None and mode_prop.value_list:
            modes = QHBoxLayout()
            modes.setSpacing(8)
            for item in mode_prop.value_list[:4]:
                desc = (
                    item.get("description")
                    or item.get("desc_zh_cn")
                    or str(item.get("value"))
                )
                btn = QPushButton(str(desc))
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(self._mode_btn_qss())
                value = item.get("value")
                btn.clicked.connect(
                    lambda _=False, p=mode_prop.name, v=value:
                    self.prop_write_requested.emit(device.did, p, v))
                modes.addWidget(btn)
            lay.addLayout(modes)

        step, tmin, tmax = 1.0, 16.0, 30.0
        tprop = self._find_prop(detail, ("target-temperature", "target_temperature"))
        if tprop is not None and tprop.range:
            tmin, tmax, step = tprop.range

        def _bump(delta: float) -> None:
            if target is None or tprop is None:
                return
            new_v = min(max(target + delta, tmin), tmax)
            self.prop_write_requested.emit(device.did, tprop.name, new_v)

        minus.clicked.connect(lambda: _bump(-step))
        plus.clicked.connect(lambda: _bump(step))

        power_btn = QPushButton(
            "关闭空调" if self._known_power.get(device.did) else "开启空调")
        power_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        power_btn.setFixedHeight(36)
        power_btn.setStyleSheet(
            f"QPushButton {{ background: {SiColors.SURFACE}; border: 1px solid {SiColors.LINE};"
            f" border-radius: 10px; color: {SiColors.TEXT_PRIMARY}; }}"
            f"QPushButton:hover {{ border-color: {SiColors.THEME}; color: {SiColors.THEME}; }}")
        power_btn.clicked.connect(lambda: self.power_toggled.emit(device.did))
        lay.addWidget(power_btn)
        return card

    @staticmethod
    def _circle_btn_qss() -> str:
        return (
            f"QPushButton {{ background: {SiColors.SURFACE}; border: none; border-radius: 20px;"
            f" color: {SiColors.TEXT_PRIMARY}; font-size: 16pt; }}"
            f"QPushButton:hover {{ background: {SiColors.BTN_HOVER}; }}"
        )

    @staticmethod
    def _mode_btn_qss() -> str:
        return (
            f"QPushButton {{ background: {SiColors.SURFACE}; border: 1px solid {SiColors.LINE};"
            f" border-radius: 8px; padding: 6px 10px; color: {SiColors.TEXT_SECONDARY}; }}"
            f"QPushButton:hover {{ border-color: {SiColors.THEME}; color: {SiColors.THEME}; }}"
        )

    @staticmethod
    def _find_prop(
        detail: DeviceDetail | None, names: tuple[str, ...]
    ) -> PropInfo | None:
        if detail is None:
            return None
        for p in detail.props:
            if p.name in names or any(p.name.endswith(n) for n in names):
                return p
        return None
