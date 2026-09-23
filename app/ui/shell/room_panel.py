# SPDX-License-Identifier: GPL-3.0-or-later
# MiHome-Windows: 米家设备的 Windows 桌面控制端
"""右侧房间面板：分类设备列表 + 空调深控卡。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
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

_MODE_ICON = {
    "制冷": "mdi.snowflake",
    "cool": "mdi.snowflake",
    "制热": "mdi.fire",
    "heat": "mdi.fire",
    "自动": "mdi.autorenew",
    "auto": "mdi.autorenew",
    "除湿": "mdi.water",
    "dry": "mdi.water",
    "送风": "mdi.fan",
    "fan": "mdi.fan",
    "通风": "mdi.fan",
}


def _mode_icon(text: str) -> str:
    key = str(text).strip().lower()
    for k, icon in _MODE_ICON.items():
        if k in key:
            return icon
    return "mdi.tune-variant"


class RoomPanel(QFrame):
    """房间详情侧栏。业务读写由 MainWindow / JobExecutor 承担。"""

    closed = Signal()
    device_selected = Signal(str)
    power_toggled = Signal(str)
    power_many_requested = Signal(list, bool)  # dids, on
    open_scenes_requested = Signal()
    prop_write_requested = Signal(str, str, object)  # did, prop_name, value

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rightPanel")
        self.setFixedWidth(360)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(18, 16, 12, 16)
        self._title = QLabel("房间")
        self._title.setFont(QFont("Microsoft YaHei UI", 15, QFont.Weight.DemiBold))
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
        self._body_lay.addWidget(self._room_banner())
        self._body_lay.addWidget(self._environment_card())

        groups: dict[str, list[DeviceInfo]] = {}
        for d in self._devices:
            groups.setdefault(classify_device(d), []).append(d)

        for key, icon, label in _KIND_META:
            items = groups.get(key)
            if not items:
                continue
            # 空调从分类列表抽出，放到深控卡，避免重复一行空壳
            if key == "climate" and any(d.online for d in items):
                climate = next(d for d in items if d.online)
                self._body_lay.addWidget(self._climate_card(climate))
                rest = [d for d in items if d.did != climate.did]
                if rest:
                    self._body_lay.addWidget(self._section_header(icon, label, rest))
                    for d in rest:
                        self._body_lay.addWidget(self._device_row(d))
                continue
            self._body_lay.addWidget(self._section_header(icon, label, items, bulk=(key == "light")))
            for d in items:
                self._body_lay.addWidget(self._device_row(d))

        self._body_lay.addStretch(1)

    def _environment_card(self) -> QWidget:
        from app.ui.shell.rooms_page import _metric_pair
        temp, humidity = _metric_pair(self._devices, self._metrics)
        card = QFrame()
        card.setObjectName("homeSectionCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(14, 13, 14, 13)
        for title, value in (("室内温度", temp), ("室内湿度", humidity)):
            col = QVBoxLayout()
            name = QLabel(title)
            name.setStyleSheet(f"color: {SiColors.TEXT_MUTED}; font-size: 8pt;")
            number = QLabel(value)
            number.setStyleSheet(
                f"color: {SiColors.TEXT_PRIMARY}; font-size: 14pt; font-weight: 600;")
            col.addWidget(name)
            col.addWidget(number)
            lay.addLayout(col, 1)
        return card

    def _room_banner(self) -> QWidget:
        from app.ui.shell.home_page import _SoftCover, _ROOM_COVER, _ROOM_IMAGE
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(0, 0, 0, 4)
        cover = _SoftCover(
            _ROOM_COVER.get(self._room_name, _ROOM_COVER["未分配"]),
            image_name=_ROOM_IMAGE.get(self._room_name, "room-photo-living.png"),
            height=160, radius=18)
        lay.addWidget(cover)
        online = sum(1 for d in self._devices if d.online)
        meta = QLabel(f"{len(self._devices)} 台设备 · {online} 在线")
        meta.setStyleSheet(
            f"color: {SiColors.TEXT_SECONDARY}; background: transparent;"
            f" font-size: 9pt; padding: 6px 2px 0 2px;")
        lay.addWidget(meta)
        return host

    def _section_header(
        self, icon: str, label: str, items: list[DeviceInfo], bulk: bool = False
    ) -> QWidget:
        row = QHBoxLayout()
        ic = QLabel()
        ic.setPixmap(qta.icon(icon, color=SiColors.THEME).pixmap(18, 18))
        row.addWidget(ic)
        on = sum(1 for d in items if self._known_power.get(d.did) is True)
        text = QLabel(f"{label} · {len(items)} 台")
        text.setStyleSheet(f"color: {SiColors.TEXT_PRIMARY}; background: transparent;")
        row.addWidget(text)
        row.addStretch(1)
        if bulk:
            light_dids = [d.did for d in items
                          if d.online and self._known_power.get(d.did) is not None]
            for title, turn_on in (("全开", True), ("全关", False)):
                btn = QPushButton(title)
                btn.setEnabled(bool(light_dids))
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(
                    f"QPushButton {{ background: {SiColors.SURFACE}; border: none;"
                    f" border-radius: 8px; padding: 4px 10px;"
                    f" color: {SiColors.TEXT_SECONDARY}; }}"
                    f"QPushButton:hover {{ background: {SiColors.BTN_HOVER};"
                    f" color: {SiColors.THEME}; }}")
                btn.clicked.connect(
                    lambda _=False, ds=light_dids, on_flag=turn_on:
                    self.power_many_requested.emit(ds, on_flag))
                row.addWidget(btn)
                row.addSpacing(6)
            scene_btn = QPushButton("场景")
            scene_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            scene_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none;"
                f" padding: 4px 8px; color: {SiColors.THEME}; }}"
                f"QPushButton:hover {{ color: {SiColors.THEME_HOVER}; }}")
            scene_btn.clicked.connect(self.open_scenes_requested.emit)
            row.addWidget(scene_btn)
        else:
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
        state = self._known_power.get(device.did)
        if device.online and state is not None:
            power = QPushButton()
            power.setFixedSize(32, 32)
            power.setCursor(Qt.CursorShape.PointingHandCursor)
            icon = "mdi.power" if state else "mdi.power-off"
            power.setIcon(qta.icon(icon, color=SiColors.THEME if state else SiColors.ICON_DIM))
            power.setStyleSheet(
                f"QPushButton {{ background: {SiColors.SURFACE}; border: none; border-radius: 16px; }}"
                f"QPushButton:hover {{ background: {SiColors.BTN_HOVER}; }}")
            power.clicked.connect(lambda: self.power_toggled.emit(device.did))
            lay.addWidget(power)
        return card

    def _climate_card(self, device: DeviceInfo) -> QWidget:
        card = QFrame()
        card.setObjectName("climateCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 18)
        lay.setSpacing(14)

        head = QHBoxLayout()
        name_col = QVBoxLayout()
        name_col.setSpacing(2)
        name = QLabel(f"{self._room_name}{device.name}" if self._room_name else device.name)
        name.setFont(QFont("Microsoft YaHei UI", 13, QFont.Weight.DemiBold))
        name.setStyleSheet(
            f"color: {SiColors.TEXT_PRIMARY}; background: transparent;")
        name_col.addWidget(name)
        state = self._known_power.get(device.did)
        on = state is True
        running = QLabel("●  已开启" if on else "○  已关闭" if state is False else "开关状态未获取")
        running.setStyleSheet(
            f"color: {SiColors.THEME if on else SiColors.TEXT_MUTED};"
            f" background: transparent; font-size: 9pt;")
        name_col.addWidget(running)
        head.addLayout(name_col, 1)
        more = QLabel()
        more.setPixmap(qta.icon("mdi.dots-horizontal", color=SiColors.TEXT_MUTED).pixmap(18, 18))
        head.addWidget(more)
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
        fan_level = values.get("fan-level") or values.get("fan_level") or values.get("wind-speed")

        # 大温度区
        temp_wrap = QWidget()
        temp_lay = QHBoxLayout(temp_wrap)
        temp_lay.setContentsMargins(0, 4, 0, 4)
        minus = QPushButton("−")
        minus.setFixedSize(42, 42)
        minus.setStyleSheet(self._circle_btn_qss())
        minus.setCursor(Qt.CursorShape.PointingHandCursor)
        plus = QPushButton("+")
        plus.setFixedSize(42, 42)
        plus.setStyleSheet(self._circle_btn_qss())
        plus.setCursor(Qt.CursorShape.PointingHandCursor)

        center = QVBoxLayout()
        center.setSpacing(0)
        label = QLabel("设定温度")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"color: {SiColors.TEXT_MUTED}; background: transparent; font-size: 9pt;")
        center.addWidget(label)
        temp_label = QLabel(f"{target:.1f}°C" if target is not None else "--°C")
        temp_label.setFont(QFont("Microsoft YaHei UI", 30, QFont.Weight.DemiBold))
        temp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        temp_label.setStyleSheet(
            f"color: {SiColors.TEXT_PRIMARY}; background: transparent;")
        center.addWidget(temp_label)
        temp_lay.addWidget(minus)
        temp_lay.addLayout(center, 1)
        temp_lay.addWidget(plus)
        lay.addWidget(temp_wrap)

        meta_parts = []
        if current is not None:
            meta_parts.append(f"室内 {current:.0f}°")
        if humidity is not None:
            meta_parts.append(f"湿度 {humidity:.0f}%")
        if fan_level is not None:
            try:
                meta_parts.append(f"风速 {int(float(fan_level))} 档")
            except (TypeError, ValueError):
                meta_parts.append(f"风速 {fan_level}")
        if meta_parts:
            meta = QLabel("  ".join(meta_parts))
            meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
            meta.setStyleSheet(
                f"color: {SiColors.TEXT_SECONDARY}; background: transparent;")
            lay.addWidget(meta)

        # 模式 2x2
        mode_prop = self._find_prop(detail, ("mode", "air-conditioner-mode"))
        if mode_prop is not None and mode_prop.value_list:
            lay.addWidget(self._label_row("模式"))
            grid = QGridLayout()
            grid.setSpacing(8)
            for i, item in enumerate(mode_prop.value_list[:4]):
                desc = str(
                    item.get("description")
                    or item.get("desc_zh_cn")
                    or item.get("value")
                )
                grid.addWidget(self._mode_tile(device.did, mode_prop.name, item.get("value"), desc),
                               i // 2, i % 2)
            lay.addLayout(grid)

        # 风速
        fan_prop = self._find_prop(
            detail, ("fan-level", "fan_level", "wind-speed", "wind_speed"))
        if fan_prop is not None and fan_prop.value_list:
            lay.addWidget(self._label_row("风速"))
            fan_row = QHBoxLayout()
            fan_row.setSpacing(8)
            for item in fan_prop.value_list[:4]:
                desc = str(
                    item.get("description")
                    or item.get("desc_zh_cn")
                    or item.get("value")
                )
                btn = QPushButton(desc)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(self._mode_btn_qss())
                value = item.get("value")
                btn.clicked.connect(
                    lambda _=False, p=fan_prop.name, v=value:
                    self.prop_write_requested.emit(device.did, p, v))
                fan_row.addWidget(btn)
            lay.addLayout(fan_row)

        step, tmin, tmax = 1.0, 16.0, 30.0
        tprop = self._find_prop(detail, ("target-temperature", "target_temperature"))
        if tprop is not None and tprop.range:
            tmin, tmax, step = tprop.range
        can_adjust = target is not None and tprop is not None and tprop.writable
        minus.setEnabled(can_adjust)
        plus.setEnabled(can_adjust)

        def _bump(delta: float) -> None:
            if target is None or tprop is None:
                return
            new_v = min(max(target + delta, tmin), tmax)
            self.prop_write_requested.emit(device.did, tprop.name, new_v)

        minus.clicked.connect(lambda: _bump(-step))
        plus.clicked.connect(lambda: _bump(step))

        power_btn = QPushButton(
            "关闭空调" if on else "开启空调" if state is False else "在详情中控制")
        power_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        power_btn.setFixedHeight(40)
        power_btn.setStyleSheet(
            f"QPushButton {{ background: {SiColors.SURFACE}; border: 1px solid {SiColors.LINE};"
            f" border-radius: 12px; color: {SiColors.TEXT_PRIMARY}; font-weight: 600; }}"
            f"QPushButton:hover {{ border-color: {SiColors.THEME}; color: {SiColors.THEME}; }}")
        if state is None:
            power_btn.clicked.connect(lambda: self.device_selected.emit(device.did))
        else:
            power_btn.clicked.connect(lambda: self.power_toggled.emit(device.did))
        lay.addWidget(power_btn)
        return card

    def _label_row(self, text: str) -> QWidget:
        lb = QLabel(text)
        lb.setStyleSheet(
            f"color: {SiColors.TEXT_MUTED}; background: transparent; font-size: 9pt;")
        return lb

    def _mode_tile(self, did: str, prop: str, value, desc: str) -> QPushButton:
        btn = QPushButton()
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumHeight(64)
        lay = QVBoxLayout(btn)
        lay.setContentsMargins(8, 10, 8, 10)
        lay.setSpacing(6)
        ic = QLabel()
        ic.setPixmap(qta.icon(_mode_icon(desc), color=SiColors.THEME).pixmap(22, 22))
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text = QLabel(desc)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setStyleSheet(
            f"color: {SiColors.TEXT_SECONDARY}; background: transparent;")
        lay.addWidget(ic)
        lay.addWidget(text)
        btn.setStyleSheet(
            f"QPushButton {{ background: {SiColors.SURFACE}; border: 1px solid {SiColors.LINE};"
            f" border-radius: 12px; }}"
            f"QPushButton:hover {{ border-color: {SiColors.THEME}; background: {SiColors.CARD_HOVER}; }}")
        btn.clicked.connect(
            lambda _=False, p=prop, v=value: self.prop_write_requested.emit(did, p, v))
        return btn

    @staticmethod
    def _circle_btn_qss() -> str:
        return (
            f"QPushButton {{ background: {SiColors.SURFACE}; border: none; border-radius: 21px;"
            f" color: {SiColors.TEXT_PRIMARY}; font-size: 18pt; }}"
            f"QPushButton:hover {{ background: {SiColors.BTN_HOVER}; }}"
        )

    @staticmethod
    def _mode_btn_qss() -> str:
        return (
            f"QPushButton {{ background: {SiColors.SURFACE}; border: 1px solid {SiColors.LINE};"
            f" border-radius: 10px; padding: 8px 10px; color: {SiColors.TEXT_SECONDARY}; }}"
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
