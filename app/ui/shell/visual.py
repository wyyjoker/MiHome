# SPDX-License-Identifier: GPL-3.0-or-later
"""卡片浮起阴影等视觉辅助。"""

from __future__ import annotations

from PySide6.QtGui import QColor, QGraphicsDropShadowEffect


def apply_card_shadow(widget, blur: int = 18, y: int = 4) -> None:
    """给卡片加轻阴影；重复调用会替换旧效果。"""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y)
    effect.setColor(QColor(43, 42, 38, 18))
    widget.setGraphicsEffect(effect)
