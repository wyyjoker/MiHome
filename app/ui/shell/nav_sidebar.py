# SPDX-License-Identifier: GPL-3.0-or-later
# MiHome-Windows: 米家设备的 Windows 桌面控制端
"""左侧全局导航栏：品牌/导航/用户区/时钟。"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import qtawesome as qta

from app.ui.si_theme import SiColors

_NAV_ITEMS = (
    ("home", "mdi.home-heart", "家庭"),
    ("rooms", "mdi.floor-plan", "房间"),
    ("devices", "mdi.devices", "设备"),
    ("scenes", "mdi.palette-swatch", "场景"),
    ("automation", "mdi.robot", "自动化"),
    ("security", "mdi.shield-home", "安防"),
    ("energy", "mdi.flash", "能耗"),
    ("messages", "mdi.message-text", "消息"),
)

_WEEKDAY = "一二三四五六日"


class _Avatar(QWidget):
    """圆形字母头像。"""

    def __init__(self, letter: str = "家", size: int = 40, parent=None):
        super().__init__(parent)
        self._letter = letter[:1] or "家"
        self.setFixedSize(size, size)

    def set_letter(self, letter: str) -> None:
        self._letter = letter[:1] or "家"
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(SiColors.THEME))
        painter.drawEllipse(self.rect())
        painter.setPen(QColor(SiColors.ON_THEME_TEXT))
        font = QFont("Microsoft YaHei UI", 12, QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._letter)


class NavSidebar(QFrame):
    """左栏：品牌 + 导航 + 底部用户/时钟。"""

    navigate = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("navSidebar")
        self.setFixedWidth(228)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 20, 16, 18)
        root.setSpacing(6)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(8)
        home_ic = QLabel()
        home_ic.setPixmap(qta.icon("mdi.home-heart", color=SiColors.THEME).pixmap(22, 22))
        brand_row.addWidget(home_ic)
        brand = QLabel("我的家")
        brand.setFont(QFont("Microsoft YaHei UI", 13, QFont.Weight.DemiBold))
        brand.setStyleSheet(f"color: {SiColors.TEXT_PRIMARY}; background: transparent;")
        brand_row.addWidget(brand)
        brand_row.addStretch(1)
        root.addLayout(brand_row)
        root.addSpacing(16)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        self._badges: dict[str, QLabel] = {}
        for key, icon, label in _NAV_ITEMS:
            btn = QPushButton(f"   {label}")
            btn.setObjectName("navItem")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIcon(qta.icon(icon, color=SiColors.TEXT_SECONDARY))
            btn.setIconSize(qta.icon(icon).pixmap(18, 18).size())
            self._group.addButton(btn)
            self._buttons[key] = btn
            btn.clicked.connect(lambda _=False, k=key: self.navigate.emit(k))
            # 消息角标（默认隐藏）
            wrap = QWidget()
            wl = QHBoxLayout(wrap)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setSpacing(0)
            wl.addWidget(btn, 1)
            badge = QLabel("0")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedSize(18, 18)
            badge.setStyleSheet(
                "background: #c0392b; color: white; border-radius: 9px;"
                " font-size: 8pt; font-weight: 700;")
            badge.hide()
            wl.addWidget(badge)
            self._badges[key] = badge
            root.addWidget(wrap)

        root.addStretch(1)

        # ── 底部：用户 + 时钟 ──
        user_card = QFrame()
        user_card.setObjectName("navUserCard")
        uc = QHBoxLayout(user_card)
        uc.setContentsMargins(10, 10, 10, 10)
        uc.setSpacing(10)
        self._avatar = _Avatar("你")
        uc.addWidget(self._avatar)
        col = QVBoxLayout()
        col.setSpacing(2)
        self._user_name = QLabel("你好")
        self._user_name.setStyleSheet(
            f"color: {SiColors.TEXT_PRIMARY}; background: transparent;"
            f" font-weight: 600;")
        self._user_role = QLabel("家庭管理员")
        self._user_role.setStyleSheet(
            f"color: {SiColors.TEXT_MUTED}; background: transparent; font-size: 8pt;")
        col.addWidget(self._user_name)
        col.addWidget(self._user_role)
        uc.addLayout(col, 1)
        root.addWidget(user_card)

        clock_box = QFrame()
        clock_box.setObjectName("navClockCard")
        cb = QVBoxLayout(clock_box)
        cb.setContentsMargins(10, 8, 10, 8)
        cb.setSpacing(2)
        self._time_label = QLabel("00:00")
        self._time_label.setFont(QFont("Microsoft YaHei UI", 26, QFont.Weight.DemiBold))
        self._time_label.setStyleSheet(
            f"color: {SiColors.TEXT_PRIMARY}; background: transparent;")
        self._date_label = QLabel("")
        self._date_label.setStyleSheet(
            f"color: {SiColors.TEXT_SECONDARY}; background: transparent; font-size: 9pt;")
        cb.addWidget(self._time_label)
        cb.addWidget(self._date_label)
        root.addWidget(clock_box)
        root.addSpacing(8)

        settings_btn = QPushButton("   设置")
        settings_btn.setObjectName("navItem")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setIcon(qta.icon("mdi.cog-outline", color=SiColors.TEXT_SECONDARY))
        settings_btn.clicked.connect(lambda: self.navigate.emit("settings"))
        self._buttons["settings"] = settings_btn
        root.addWidget(settings_btn)

        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start()
        self._tick_clock()

        self.set_current("home")

    def set_display_name(self, name: str) -> None:
        text = (name or "你好").strip() or "你好"
        self._user_name.setText(text)
        self._avatar.set_letter(text[0])

    def set_message_count(self, count: int) -> None:
        badge = self._badges.get("messages")
        if badge is None:
            return
        if count > 0:
            badge.setText(str(count) if count < 100 else "99+")
            badge.show()
        else:
            badge.hide()

    def _tick_clock(self) -> None:
        now = datetime.now()
        self._time_label.setText(now.strftime("%H:%M"))
        weekday = _WEEKDAY[now.weekday()]
        self._date_label.setText(f"{now.month}月{now.day}日 周{weekday}")

    def set_current(self, key: str) -> None:
        btn = self._buttons.get(key)
        if btn is not None and btn.isCheckable():
            btn.setChecked(True)

    def retheme(self) -> None:
        for key, btn in self._buttons.items():
            icon_name = "mdi.cog-outline" if key == "settings" else next(
                (i for k, i, _ in _NAV_ITEMS if k == key), "mdi.home-heart")
            color = SiColors.TEXT_PRIMARY if btn.isChecked() else SiColors.TEXT_SECONDARY
            btn.setIcon(qta.icon(icon_name, color=color))
        self.setStyleSheet(
            f"QFrame#navSidebar {{ background: {SiColors.NAV_BG}; "
            f"border-right: 1px solid {SiColors.LINE}; }}")
