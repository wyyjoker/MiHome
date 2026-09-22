# SPDX-License-Identifier: GPL-3.0-or-later
# MiHome-Windows: 米家设备的 Windows 桌面控制端
"""家庭首页信息流：问候、状态 chips、关注、房间卡、常用设备。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPixmap
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
    group_rooms,
    greeting_text,
    pick_common_devices,
    status_chips,
)

_ROOM_COVER = {
    "客厅": ("#F0DCC0", "#C9A574"),
    "主卧": ("#DCE4F0", "#8FA0B8"),
    "书房": ("#DCE8DC", "#8A9A88"),
    "次卧": ("#F0E0D8", "#B89888"),
    "厨房": ("#F0E8D0", "#B8A878"),
    "阳台": ("#D0E8EC", "#88A8B0"),
    "未分配": ("#E8E4DC", "#A8A298"),
}

_KIND_BADGE = {
    "light": ("mdi.lightbulb-on-outline", "灯"),
    "climate": ("mdi.snowflake", "空调"),
    "curtain": ("mdi.blinds", "窗帘"),
    "media": ("mdi.television", "影音"),
}

_ROOM_IMAGE = {
    "客厅": "room-living.png",
    "主卧": "room-master.png",
    "书房": "room-study.png",
    "次卧": "room-second.png",
    "厨房": "room-default.png",
    "阳台": "room-default.png",
    "未分配": "room-default.png",
}


def _load_asset(name: str) -> QPixmap | None:
    from pathlib import Path
    from app import resource_path
    path = resource_path(f"app/ui/shell/assets/{name}")
    if not Path(path).is_file():
        return None
    pix = QPixmap(str(path))
    return None if pix.isNull() else pix


class _SoftCover(QWidget):
    """柔和封面：优先用本地插画，缺图回退渐变色块。"""

    def __init__(
        self,
        colors: tuple[str, str],
        image_name: str | None = None,
        height: int = 96,
        radius: int = 14,
        parent=None,
    ):
        super().__init__(parent)
        self._colors = colors
        self._image_name = image_name
        self._radius = radius
        self._src: QPixmap | None = None
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(
            float(self.rect().x()), float(self.rect().y()),
            float(self.rect().width()), float(self.rect().height()),
            float(self._radius), float(self._radius),
        )
        painter.setClipPath(path)

        if self._image_name:
            if self._src is None:
                self._src = _load_asset(self._image_name)
            if self._src is not None:
                # 放大裁切到「摄影感」：略放大后居中，减少留白
                target = self.rect().size() * 1.08
                scaled = self._src.scaled(
                    target,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                x = (scaled.width() - self.width()) // 2
                y = (scaled.height() - self.height()) // 2
                painter.drawPixmap(-max(x, 0), -max(y, 0), scaled)
                # 底部轻渐变压暗，便于叠字
                grad = QLinearGradient(0, self.height() * 0.45, 0, self.height())
                grad.setColorAt(0, QColor(43, 42, 38, 0))
                grad.setColorAt(1, QColor(43, 42, 38, 70))
                painter.fillRect(self.rect(), QColor(255, 255, 255, 20))
                painter.fillRect(self.rect(), grad)
                return

        grad = QLinearGradient(0, 0, self.width() * 0.85, self.height())
        grad.setColorAt(0, QColor(self._colors[0]))
        grad.setColorAt(1, QColor(self._colors[1]))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawPath(path)
        painter.setBrush(QColor(255, 255, 255, 40))
        r = int(self.height() * 0.55)
        painter.drawEllipse(self.width() - r - 12, -r // 3, r, r)


class _SectionCard(QFrame):
    def __init__(self, title: str | None = None, parent=None, trailing: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("homeSectionCard")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 12, 14, 12)
        self._layout.setSpacing(8)
        if title or trailing is not None:
            head = QHBoxLayout()
            if title:
                t = QLabel(title)
                t.setObjectName("homeSectionTitle")
                t.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.DemiBold))
                head.addWidget(t)
            head.addStretch(1)
            if trailing is not None:
                head.addWidget(trailing)
            self._layout.addLayout(head)
        try:
            from app.ui.shell.visual import apply_card_shadow
            apply_card_shadow(self, blur=14, y=2)
        except Exception:
            pass

    def body(self) -> QVBoxLayout:
        return self._layout


class _StatusChip(QFrame):
    def __init__(self, icon_key: str, label: str, count: int, parent=None):
        super().__init__(parent)
        self.setObjectName("chipPill")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 14, 8)
        lay.setSpacing(8)
        icons = {
            "light": "mdi.lightbulb-on",
            "climate": "mdi.snowflake",
            "curtain": "mdi.blinds",
            "device": "mdi.devices",
        }
        colors = {
            "light": "#E8A317",
            "climate": SiColors.THEME,
            "curtain": SiColors.ACCENT_WARM,
            "device": SiColors.TEXT_SECONDARY,
        }
        ic = QLabel()
        ic.setPixmap(qta.icon(
            icons.get(icon_key, "mdi.information-outline"),
            color=colors.get(icon_key, SiColors.THEME),
        ).pixmap(18, 18))
        lay.addWidget(ic)
        text = QLabel(f"<b>{count}</b> {label}")
        text.setTextFormat(Qt.TextFormat.RichText)
        text.setStyleSheet(
            f"color: {SiColors.TEXT_SECONDARY}; background: transparent; font-size: 11pt;")
        lay.addWidget(text)
        self.setFixedHeight(40)


class _RoomCard(QFrame):
    clicked = Signal(str)

    def __init__(
        self,
        room: RoomSummary,
        metrics: dict[str, str | None],
        known_power: dict[str, bool | None],
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("roomCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._room = room.name
        self.setFixedWidth(156)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        cover_host = QWidget()
        cover_host.setFixedHeight(100)
        cover_lay = QVBoxLayout(cover_host)
        cover_lay.setContentsMargins(0, 0, 0, 0)
        cover = _SoftCover(
            _ROOM_COVER.get(room.name, _ROOM_COVER["未分配"]),
            image_name=_ROOM_IMAGE.get(room.name, "room-default.png"),
            height=100, radius=16)
        cover_lay.addWidget(cover)

        overlay = QWidget(cover_host)
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        overlay.setGeometry(0, 0, 156, 100)
        ov = QVBoxLayout(overlay)
        ov.setContentsMargins(14, 12, 14, 12)
        ov.addStretch(1)
        # 封面为浅色插画，深浅主题都用深字；底部有压暗时仍可读
        cover_fg = "#2B2A26"
        name = QLabel(room.name)
        name.setStyleSheet(
            f"color: {cover_fg}; background: transparent;"
            f" font-size: 13pt; font-weight: 700;")
        ov.addWidget(name)

        metric = room.metric_texts(metrics)
        temp_line = metric[0] if metric else f"{room.online} 在线"
        temp = QLabel(temp_line)
        temp.setStyleSheet(
            f"color: {cover_fg}; background: transparent;"
            f" font-size: 10pt; font-weight: 600;")
        ov.addWidget(temp)
        overlay.raise_()
        root.addWidget(cover_host)

        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(10, 8, 10, 10)
        body_lay.setSpacing(4)

        meta = QLabel(f"{len(room.devices)} 台 · {room.online} 在线")
        meta.setStyleSheet(
            f"color: {SiColors.TEXT_SECONDARY}; background: transparent; font-size: 9pt;")
        body_lay.addWidget(meta)

        badges = QHBoxLayout()
        badges.setSpacing(4)
        kinds: list[str] = []
        for d in room.devices:
            k = classify_device(d)
            if k in _KIND_BADGE and k not in kinds:
                kinds.append(k)
        for k in kinds[:3]:
            icon, text = _KIND_BADGE[k]
            on = any(
                known_power.get(d.did) is True
                for d in room.devices if classify_device(d) == k
            )
            pill = QFrame()
            pill.setStyleSheet(
                f"QFrame {{ background: {SiColors.THEME if on else SiColors.SURFACE};"
                f" border-radius: 8px; }}")
            pl = QHBoxLayout(pill)
            pl.setContentsMargins(6, 2, 6, 2)
            pl.setSpacing(3)
            ic = QLabel()
            color = SiColors.ON_THEME_TEXT if on else SiColors.TEXT_SECONDARY
            ic.setPixmap(qta.icon(icon, color=color).pixmap(12, 12))
            pl.addWidget(ic)
            lb = QLabel(text)
            lb.setStyleSheet(
                f"color: {color}; background: transparent; font-size: 8pt;")
            pl.addWidget(lb)
            badges.addWidget(pill)
        badges.addStretch(1)
        body_lay.addLayout(badges)
        root.addWidget(body)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._room)
        super().mousePressEvent(event)


class _AttentionRow(QFrame):
    open_device = Signal(str)

    def __init__(self, item: AttentionItem, parent=None):
        super().__init__(parent)
        self.setObjectName("attentionRow")
        self.setMinimumWidth(200)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)
        accent = SiColors.WARN_TEXT if item.severity == "battery" else SiColors.THEME
        icon_name = "mdi.battery-alert" if item.severity == "battery" else "mdi.wifi-off"
        badge = QFrame()
        badge.setFixedSize(32, 32)
        badge.setStyleSheet(
            f"QFrame {{ background: {accent}22; border-radius: 10px; }}")
        bl = QVBoxLayout(badge)
        bl.setContentsMargins(0, 0, 0, 0)
        ic = QLabel()
        ic.setPixmap(qta.icon(icon_name, color=accent).pixmap(16, 16))
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(ic)
        lay.addWidget(badge)
        col = QVBoxLayout()
        col.setSpacing(1)
        t = QLabel(item.title)
        t.setStyleSheet(f"color: {SiColors.TEXT_PRIMARY}; background: transparent; font-weight: 600;")
        d = QLabel(item.detail or ("电量偏低" if item.severity == "battery" else "设备离线"))
        d.setStyleSheet(
            f"color: {SiColors.TEXT_MUTED}; background: transparent; font-size: 8pt;")
        col.addWidget(t)
        col.addWidget(d)
        lay.addLayout(col, 1)
        btn = QPushButton("查看")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none;"
            f" color: {SiColors.THEME}; font-weight: 600; font-size: 9pt; }}"
            f"QPushButton:hover {{ color: {SiColors.THEME_HOVER}; }}")
        btn.clicked.connect(lambda: self.open_device.emit(item.did))
        lay.addWidget(btn)
        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel(item.title)
        t.setStyleSheet(f"color: {SiColors.TEXT_PRIMARY}; background: transparent; font-weight: 600;")
        d = QLabel(item.detail or ("电量偏低" if item.severity == "battery" else "设备离线"))
        d.setStyleSheet(
            f"color: {SiColors.TEXT_MUTED}; background: transparent; font-size: 9pt;")
        col.addWidget(t)
        col.addWidget(d)
        lay.addLayout(col, 1)
        btn = QPushButton("查看")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none;"
            f" color: {SiColors.THEME}; font-weight: 600; }}"
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
        self._root.setContentsMargins(24, 14, 24, 18)
        self._root.setSpacing(12)
        self.setWidget(self._host)

        self._devices: list[DeviceInfo] = []
        self._known_power: dict[str, bool | None] = {}
        self._metrics: dict[str, str | None] = {}
        self._display_name = "你好"
        self._tray_dids: list[str] = []
        self._consumables: list = []
        self._weather: object | None = None

    def set_display_name(self, name: str) -> None:
        self._display_name = name or "你好"

    def set_weather(self, snapshot) -> None:
        """WeatherSnapshot 或 None。"""
        self._weather = snapshot
        # 仅刷新顶栏，避免整页重建闪烁
        if self._root.count() > 0:
            header = self._root.itemAt(0).widget()
            if header is not None:
                # 重建整个页最简单且频率低（约 15 分钟一次）
                self._rebuild()

    def update_data(
        self,
        devices: list[DeviceInfo],
        known_power: dict[str, bool | None],
        metrics: dict[str, str | None],
        tray_dids: list[str] | None = None,
        consumables: list | None = None,
    ) -> None:
        self._devices = list(devices)
        self._known_power = dict(known_power)
        self._metrics = dict(metrics)
        self._tray_dids = list(tray_dids or [])
        self._consumables = list(consumables or [])
        self._rebuild()

    def _clear(self) -> None:
        while self._root.count():
            item = self._root.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _rebuild(self) -> None:
        self._clear()
        self._root.addWidget(self._build_header())

        chips = status_chips(self._devices, self._known_power)
        self._root.addWidget(self._build_banner(chips))

        attention = build_attention(
            self._devices, self._known_power, consumables=self._consumables)
        if attention:
            self._root.addWidget(self._build_attention(attention))

        rooms = group_rooms(self._devices)
        if rooms:
            self._root.addWidget(self._build_rooms(rooms))
        elif not self._devices:
            self._root.addWidget(self._build_empty())

        common = pick_common_devices(
            self._devices, self._known_power, self._tray_dids)
        if common:
            self._root.addWidget(self._build_common(common))

        self._root.addStretch(1)

    def _build_empty(self) -> QWidget:
        card = _SectionCard()
        host = QWidget()
        col = QVBoxLayout(host)
        col.setContentsMargins(0, 4, 0, 4)
        col.setSpacing(8)
        cover = _SoftCover(
            (SiColors.BANNER_A, SiColors.BANNER_B),
            image_name="room-default.png",
            height=120, radius=16)
        col.addWidget(cover)
        tip = QLabel("暂无设备数据\n刷新后将显示房间与常用设备")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip.setStyleSheet(
            f"color: {SiColors.TEXT_SECONDARY}; background: transparent; font-size: 11pt;")
        tip.setWordWrap(True)
        col.addWidget(tip)
        card.body().addWidget(host)
        return card

    def _build_header(self) -> QWidget:
        row = QHBoxLayout()
        title = QLabel("家庭")
        title.setFont(QFont("Microsoft YaHei UI", 20, QFont.Weight.DemiBold))
        title.setStyleSheet(
            f"color: {SiColors.TEXT_PRIMARY}; background: transparent;")
        row.addWidget(title)
        row.addStretch(1)

        w = self._weather
        if w is not None:
            parts = []
            temp = getattr(w, "temperature", None)
            if temp is not None:
                parts.append(f"{temp:.0f}°C")
            text = getattr(w, "weather_text", "") or ""
            if text:
                parts.append(text)
            aqi = getattr(w, "aqi", None)
            aqi_text = getattr(w, "aqi_text", "") or ""
            if aqi is not None:
                parts.append(f"空气{aqi_text or '—'} {aqi}")
            if parts:
                weather = QLabel("  ".join(parts))
                weather.setStyleSheet(
                    f"color: {SiColors.TEXT_SECONDARY}; background: transparent;"
                    f" font-size: 10pt;")
                row.addWidget(weather)
                row.addSpacing(12)

        online = sum(1 for d in self._devices if d.online)
        if self._devices:
            pill = QLabel(f"  ●  {online} 台在线")
            pill.setStyleSheet(
                f"color: {SiColors.THEME}; background: transparent; font-size: 10pt;")
            row.addWidget(pill)
            row.addSpacing(12)
        refresh = QPushButton()
        refresh.setFixedSize(36, 36)
        refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh.setIcon(qta.icon("mdi.refresh", color=SiColors.TEXT_SECONDARY))
        refresh.setStyleSheet(
            f"QPushButton {{ background: {SiColors.CARD}; border: 1px solid {SiColors.LINE};"
            f" border-radius: 12px; }}"
            f"QPushButton:hover {{ background: {SiColors.CARD_HOVER}; }}")
        refresh.clicked.connect(self.refresh_requested.emit)
        row.addWidget(refresh)
        host = QWidget()
        host.setLayout(row)
        return host

    def _build_banner(self, chips: list[tuple[str, str, int]] | None = None) -> QWidget:
        card = QFrame()
        card.setObjectName("homeBanner")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 14, 14)
        lay.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(14)
        col = QVBoxLayout()
        col.setSpacing(4)
        hello = f"{greeting_text()}，{self._display_name}"
        title = QLabel(hello)
        title.setObjectName("greetingTitle")
        title.setFont(QFont("Microsoft YaHei UI", 20, QFont.Weight.DemiBold))
        col.addWidget(title)

        online = sum(1 for d in self._devices if d.online)
        offline = len(self._devices) - online
        if not self._devices:
            sub_text = "正在同步家庭设备…"
        elif offline:
            sub_text = f"有 {offline} 台设备离线，{online} 台在线"
        else:
            sub_text = f"家里目前一切正常"
        sub = QLabel(sub_text)
        sub.setObjectName("greetingSub")
        sub.setFont(QFont("Microsoft YaHei UI", 11))
        col.addWidget(sub)
        col.addStretch(1)
        top.addLayout(col, 1)

        cover = _SoftCover(
            (SiColors.BANNER_A, SiColors.BANNER_B),
            image_name="banner-home.png",
            height=96, radius=16)
        cover.setFixedWidth(180)
        top.addWidget(cover)
        lay.addLayout(top)

        if chips:
            chip_row = QHBoxLayout()
            chip_row.setSpacing(8)
            for key, label, count in chips:
                chip_row.addWidget(_StatusChip(key, label, count))
            chip_row.addStretch(1)
            lay.addLayout(chip_row)
        return card

    def _build_chips(self, chips: list[tuple[str, str, int]]) -> QWidget:
        row = QHBoxLayout()
        row.setSpacing(10)
        for key, label, count in chips:
            row.addWidget(_StatusChip(key, label, count))
        row.addStretch(1)
        host = QWidget()
        host.setLayout(row)
        return host

    def _build_attention(self, items: list[AttentionItem]) -> QWidget:
        card = _SectionCard("需要关注")
        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        for i, item in enumerate(items[:4]):
            row = _AttentionRow(item)
            row.open_device.connect(self.device_selected.emit)
            grid.addWidget(row, i // 2, i % 2)
        card.body().addWidget(grid_host)
        return card

    def _build_rooms(self, rooms: list[RoomSummary]) -> QWidget:
        card = _SectionCard("房间")
        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        cols = 4
        for i, room in enumerate(rooms):
            rc = _RoomCard(room, self._metrics, self._known_power)
            rc.clicked.connect(self.room_selected.emit)
            grid.addWidget(rc, i // cols, i % cols)
        card.body().addWidget(grid_host)
        return card

    def _build_common(self, devices: list[DeviceInfo]) -> QWidget:
        edit_btn = QPushButton("编辑")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none;"
            f" color: {SiColors.TEXT_SECONDARY}; }}"
            f"QPushButton:hover {{ color: {SiColors.THEME}; }}")
        card = _SectionCard("常用设备", trailing=edit_btn)
        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        cols = 5
        for i, d in enumerate(devices):
            grid.addWidget(self._build_common_row(d), i // cols, i % cols)
        card.body().addWidget(grid_host)
        return card

    def _build_common_row(self, device: DeviceInfo) -> QWidget:
        """效果图式竖卡：大图标 + 名称/房间 · 状态 + 底部开关。"""
        row = QFrame()
        row.setObjectName("commonDeviceCard")
        row.setFixedWidth(148)
        lay = QVBoxLayout(row)
        lay.setContentsMargins(12, 12, 12, 10)
        lay.setSpacing(6)

        kind = classify_device(device)
        icon_name = {
            "light": "mdi.ceiling-light",
            "climate": "mdi.air-conditioner",
            "curtain": "mdi.blinds",
            "media": "mdi.television",
        }.get(kind, "mdi.devices")
        state = self._known_power.get(device.did)
        on = state is True
        badge = QFrame()
        badge.setFixedSize(56, 56)
        badge.setStyleSheet(
            f"QFrame {{ background: {SiColors.THEME if on else SiColors.SURFACE};"
            f" border-radius: 16px; }}")
        bl = QVBoxLayout(badge)
        bl.setContentsMargins(0, 0, 0, 0)
        ic = QLabel()
        ic.setPixmap(qta.icon(
            icon_name,
            color=SiColors.ON_THEME_TEXT if on else SiColors.TEXT_SECONDARY,
        ).pixmap(28, 28))
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(ic)
        icon_row = QHBoxLayout()
        icon_row.addWidget(badge)
        icon_row.addStretch(1)
        lay.addLayout(icon_row)

        name = QLabel(device.name)
        name.setStyleSheet(
            f"color: {SiColors.TEXT_PRIMARY}; background: transparent;"
            f" font-size: 10pt; font-weight: 600;")
        name.setCursor(Qt.CursorShape.PointingHandCursor)
        name.mousePressEvent = (
            lambda e, did=device.did: self.device_selected.emit(did)
            if e.button() == Qt.MouseButton.LeftButton else None
        )
        lay.addWidget(name)

        if not device.online:
            status = "离线"
        elif state is True:
            status = {"light": "已点亮", "climate": "制冷中", "curtain": "已打开"}.get(kind, "运行中")
        elif state is False:
            status = "已关闭"
        else:
            status = "—"
        sub = QLabel(f"{device.room_name or device.home_name} · {status}")
        sub.setStyleSheet(
            f"color: {SiColors.TEXT_MUTED}; background: transparent; font-size: 8pt;")
        lay.addWidget(sub)
        lay.addStretch(1)

        foot = QHBoxLayout()
        foot.addWidget(QLabel())
        foot.addStretch(1)
        switch = QPushButton()
        switch.setFixedSize(44, 26)
        switch.setCursor(Qt.CursorShape.PointingHandCursor)
        switch.setEnabled(device.online)
        switch.setStyleSheet(
            f"QPushButton {{ background: {SiColors.THEME if on else SiColors.STATE_OFF};"
            f" border: none; border-radius: 13px; }}"
            f"QPushButton:hover {{ background:"
            f" {SiColors.THEME_HOVER if on else SiColors.BTN_HOVER}; }}")
        thumb = QLabel(switch)
        thumb.setFixedSize(20, 20)
        thumb.setStyleSheet(f"background: {SiColors.WHITE}; border-radius: 10px;")
        thumb.move(22 if on else 2, 3)
        switch.clicked.connect(lambda: self.power_toggled.emit(device.did))
        foot.addWidget(switch)
        lay.addLayout(foot)
        return row
        thumb.move(22 if on else 2, 3)
        switch.clicked.connect(lambda: self.power_toggled.emit(device.did))
        lay.addWidget(switch)
        return row
