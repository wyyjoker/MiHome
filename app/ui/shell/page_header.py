# SPDX-License-Identifier: GPL-3.0-or-later
"""五个主页面共用的标题与家庭状态栏。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

import qtawesome as qta

from app.ui.si_theme import SiColors


_PAGES = {
    "home": ("家庭", "家的温度，始终在你身边"),
    "rooms": ("房间", "按空间管理设备，打造更舒适的生活场景"),
    "devices": ("设备", "管理全屋智能设备，让生活更简单"),
    "scenes": ("场景", "让家主动关心你，场景联动美好生活"),
    "messages": ("消息", "关注家的每一个重要时刻"),
    "automation": ("自动化", "联动你的智能设备"),
    "security": ("安防", "关注家的安全状态"),
    "energy": ("能耗", "了解设备能源使用情况"),
}


class PageHeader(QFrame):
    notifications_requested = Signal()
    home_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("shellPageHeader")
        self.setFixedHeight(88)
        self._weather = None
        self._home_name = "我的家"
        self._message_count = 0
        self._display_name = "你"

        root = QHBoxLayout(self)
        root.setContentsMargins(28, 14, 24, 10)
        root.setSpacing(10)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self._title = QLabel()
        self._title.setFont(QFont("Microsoft YaHei UI", 20, QFont.Weight.Bold))
        self._subtitle = QLabel()
        self._subtitle.setFont(QFont("Microsoft YaHei UI", 10))
        title_col.addWidget(self._title)
        title_col.addWidget(self._subtitle)
        root.addLayout(title_col, 1)

        self._location = QPushButton()
        self._location.setObjectName("shellHeaderPill")
        self._location.setMinimumHeight(34)
        self._location.setCursor(Qt.CursorShape.PointingHandCursor)
        self._location.clicked.connect(self.home_requested.emit)
        root.addWidget(self._location)

        self._weather_label = QLabel()
        self._weather_label.setObjectName("shellHeaderPill")
        self._weather_label.setMinimumHeight(34)
        self._weather_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._weather_label)

        self._aqi_label = QLabel()
        self._aqi_label.setObjectName("shellHeaderPill")
        self._aqi_label.setMinimumHeight(34)
        self._aqi_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._aqi_label)

        self._bell = QPushButton()
        self._bell.setFixedSize(34, 34)
        self._bell.setCursor(Qt.CursorShape.PointingHandCursor)
        self._bell.setToolTip("查看消息")
        self._bell.clicked.connect(self.notifications_requested.emit)
        root.addWidget(self._bell)

        self._avatar = QLabel("你")
        self._avatar.setObjectName("shellHeaderAvatar")
        self._avatar.setFixedSize(34, 34)
        self._avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._avatar)

        self.set_page("home")
        self.retheme()

    def set_page(self, key: str) -> None:
        title, subtitle = _PAGES.get(key, ("家庭", "家的温度，始终在你身边"))
        self._title.setText(title)
        self._subtitle.setText(subtitle)

    def set_context(self, home_name: str, weather, message_count: int, display_name: str) -> None:
        self._home_name = home_name if home_name and home_name not in ("全部家庭", "全部") else "我的家"
        self._weather = weather
        self._message_count = max(0, int(message_count))
        self._display_name = (display_name or "你").strip() or "你"
        self._render_context()

    def _render_context(self) -> None:
        self._location.setText(f"  {self._home_name}  ")
        self._location.setToolTip("切换家庭")
        temp = getattr(self._weather, "temperature", None)
        sky = getattr(self._weather, "weather_text", "") if self._weather else ""
        if temp is None and not sky:
            self._weather_label.hide()
        else:
            value = f"{temp:.0f}°C" if temp is not None else ""
            self._weather_label.setText(f"  ☀  {value}  {sky}  ")
            self._weather_label.show()
        aqi = getattr(self._weather, "aqi", None)
        if aqi is None:
            self._aqi_label.hide()
        else:
            label = getattr(self._weather, "aqi_text", "") or ""
            self._aqi_label.setText(f"  AQI {aqi}  {label}  ")
            self._aqi_label.show()
        self._bell.setToolTip(
            f"查看消息（{self._message_count} 条）" if self._message_count else "查看消息")
        self._avatar.setText(self._display_name[:1])
        self.retheme()
        self._apply_density()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_density()

    def _apply_density(self) -> None:
        if not hasattr(self, "_aqi_label"):
            return
        self._subtitle.setVisible(self.width() >= 650)
        has_weather = self._weather is not None and (
            getattr(self._weather, "temperature", None) is not None
            or bool(getattr(self._weather, "weather_text", "")))
        self._weather_label.setVisible(has_weather and self.width() >= 780)
        self._aqi_label.setVisible(
            self._weather is not None
            and getattr(self._weather, "aqi", None) is not None
            and self.width() >= 980)

    def home_anchor(self) -> QPushButton:
        return self._location

    def retheme(self) -> None:
        self._title.setStyleSheet(f"color: {SiColors.TEXT_PRIMARY}; background: transparent;")
        self._subtitle.setStyleSheet(f"color: {SiColors.TEXT_SECONDARY}; background: transparent;")
        for pill in (self._location, self._weather_label, self._aqi_label):
            pill.setStyleSheet(
                f"background: {SiColors.CARD}; color: {SiColors.TEXT_PRIMARY};"
                f"border: 1px solid {SiColors.CHIP_BORDER}; border-radius: 17px;"
                "padding: 0 8px; font-size: 9pt;")
        self._location.setIcon(qta.icon("mdi.home-outline", color=SiColors.TEXT_PRIMARY))
        self._bell.setIcon(qta.icon("mdi.bell-outline", color=SiColors.TEXT_PRIMARY))
        self._bell.setText("•" if self._message_count else "")
        self._bell.setStyleSheet(
            f"QPushButton {{ background: {SiColors.CARD}; color: {SiColors.ERROR_TEXT};"
            f" border: 1px solid {SiColors.CHIP_BORDER}; border-radius: 17px; }}"
            f"QPushButton:hover {{ background: {SiColors.CARD_HOVER}; }}")
        self._avatar.setStyleSheet(
            f"background: {SiColors.THEME}; color: {SiColors.WHITE};"
            "border-radius: 17px; font-weight: 700;")
