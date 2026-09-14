# SPDX-License-Identifier: GPL-3.0-or-later
# MiHome-Windows: 米家设备的 Windows 桌面控制端
"""未接入业务的侧栏页面占位。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

import qtawesome as qta

from app.ui.si_theme import SiColors

_PRESET = {
    "scenes": ("mdi.palette-swatch", "场景", "场景编排尚未接入云端，请先在米家 App 配置。"),
    "automation": ("mdi.robot", "自动化", "自动化规则将在后续版本提供。"),
    "security": ("mdi.shield-home", "安防", "安防服务依赖更多设备与云端能力，即将支持。"),
    "energy": ("mdi.flash", "能耗", "能耗统计即将支持。"),
    "messages": ("mdi.message-text", "消息", "消息中心即将支持。"),
}


class PlaceholderPage(QWidget):
    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        icon_name, title, sub = _PRESET.get(
            key, ("mdi.clock-outline", "即将支持", "该模块暂未开放。"))

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color=SiColors.TEXT_MUTED).pixmap(48, 48))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("placeholderTitle")
        title_lbl.setFont(QFont("Microsoft YaHei UI", 16, QFont.Weight.DemiBold))
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        sub_lbl = QLabel(sub)
        sub_lbl.setObjectName("placeholderSub")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl.setWordWrap(True)
        layout.addWidget(sub_lbl)
