# SPDX-License-Identifier: GPL-3.0-or-later
# MiHome-Windows: 米家设备的 Windows 桌面控制端
"""左侧全局导航栏。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QLabel,
    QPushButton,
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


class NavSidebar(QFrame):
    """左栏：品牌区 + 导航项 + 底部设置入口。"""

    navigate = Signal(str)  # route key

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("navSidebar")
        self.setFixedWidth(208)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 18, 14, 16)
        root.setSpacing(6)

        brand = QLabel("  我的家")
        brand.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.DemiBold))
        brand.setStyleSheet(
            f"color: {SiColors.TEXT_PRIMARY}; background: transparent;")
        root.addWidget(brand)
        root.addSpacing(12)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        for key, icon, label in _NAV_ITEMS:
            btn = QPushButton(f"   {label}")
            btn.setObjectName("navItem")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setIcon(qta.icon(icon, color=SiColors.TEXT_SECONDARY))
            btn.setIconSize(qta.icon(icon).availableSizes()[0] if False else qta.icon(icon).pixmap(18, 18).size())
            self._group.addButton(btn)
            self._buttons[key] = btn
            btn.clicked.connect(lambda _=False, k=key: self.navigate.emit(k))
            root.addWidget(btn)

        root.addStretch(1)

        settings_btn = QPushButton("   设置")
        settings_btn.setObjectName("navItem")
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.setIcon(qta.icon("mdi.cog-outline", color=SiColors.TEXT_SECONDARY))
        settings_btn.clicked.connect(lambda: self.navigate.emit("settings"))
        self._buttons["settings"] = settings_btn
        root.addWidget(settings_btn)

        self.set_current("home")

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
