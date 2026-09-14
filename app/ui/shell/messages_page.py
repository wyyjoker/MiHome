# SPDX-License-Identifier: GPL-3.0-or-later
# MiHome-Windows: 米家设备的 Windows 桌面控制端
"""消息页：米家消息中心近 N 小时通知。"""

from __future__ import annotations

from datetime import datetime

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

from app.core.models import MessageInfo
from app.ui.si_theme import SiColors


class MessagesPage(QScrollArea):
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._host = QWidget()
        self._host.setObjectName("shellRoot")
        self._root = QVBoxLayout(self._host)
        self._root.setContentsMargins(32, 20, 32, 24)
        self._root.setSpacing(14)
        self.setWidget(self._host)

        self._messages: list[MessageInfo] = []
        self._rebuild()

    def set_messages(self, messages: list[MessageInfo]) -> None:
        self._messages = list(messages)
        self._rebuild()

    def _clear(self) -> None:
        while self._root.count():
            item = self._root.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _rebuild(self) -> None:
        self._clear()
        header = QHBoxLayout()
        title = QLabel("消息")
        title.setFont(QFont("Microsoft YaHei UI", 20, QFont.Weight.DemiBold))
        title.setStyleSheet(
            f"color: {SiColors.TEXT_PRIMARY}; background: transparent;")
        header.addWidget(title)
        header.addStretch(1)
        count = QLabel(f"近 24 小时 · {len(self._messages)} 条")
        count.setStyleSheet(
            f"color: {SiColors.TEXT_SECONDARY}; background: transparent;")
        header.addWidget(count)
        header.addSpacing(12)
        refresh = QPushButton()
        refresh.setFixedSize(38, 38)
        refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh.setIcon(qta.icon("mdi.refresh", color=SiColors.TEXT_SECONDARY))
        refresh.setStyleSheet(
            f"QPushButton {{ background: {SiColors.CARD}; border: 1px solid {SiColors.LINE};"
            f" border-radius: 12px; }}"
            f"QPushButton:hover {{ background: {SiColors.CARD_HOVER}; }}")
        refresh.clicked.connect(self.refresh_requested.emit)
        header.addWidget(refresh)
        host = QWidget()
        host.setLayout(header)
        self._root.addWidget(host)

        if not self._messages:
            empty = QLabel("暂无新消息\n设备告警与通知会出现在这里")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(
                f"color: {SiColors.TEXT_SECONDARY}; background: transparent; font-size: 11pt;")
            empty.setWordWrap(True)
            wrap = QWidget()
            wl = QVBoxLayout(wrap)
            wl.addStretch(1)
            wl.addWidget(empty)
            wl.addStretch(1)
            wrap.setMinimumHeight(260)
            self._root.addWidget(wrap)
            return

        for msg in self._messages[:50]:
            self._root.addWidget(self._row(msg))
        self._root.addStretch(1)

    def _row(self, msg: MessageInfo) -> QWidget:
        card = QFrame()
        card.setObjectName("commonDeviceCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)
        badge = QFrame()
        badge.setFixedSize(40, 40)
        badge.setStyleSheet(
            f"QFrame {{ background: {SiColors.SURFACE}; border-radius: 12px; }}")
        bl = QVBoxLayout(badge)
        bl.setContentsMargins(0, 0, 0, 0)
        ic = QLabel()
        ic.setPixmap(qta.icon("mdi.bell-outline", color=SiColors.THEME).pixmap(20, 20))
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(ic)
        lay.addWidget(badge)

        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel(msg.title)
        t.setStyleSheet(
            f"color: {SiColors.TEXT_PRIMARY}; background: transparent;"
            f" font-size: 11pt; font-weight: 600;")
        body = msg.body.strip()
        sub_parts = []
        if body:
            sub_parts.append(body[:80])
        if msg.timestamp:
            when = datetime.fromtimestamp(msg.timestamp)
            sub_parts.append(when.strftime("%m-%d %H:%M"))
        sub = QLabel("  ·  ".join(sub_parts) if sub_parts else "—")
        sub.setStyleSheet(
            f"color: {SiColors.TEXT_MUTED}; background: transparent; font-size: 9pt;")
        sub.setWordWrap(True)
        col.addWidget(t)
        col.addWidget(sub)
        lay.addLayout(col, 1)
        return card
