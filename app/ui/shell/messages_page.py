# SPDX-License-Identifier: GPL-3.0-or-later
"""消息中心：分类列表与真实消息详情。"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)
import qtawesome as qta

from app.core.models import MessageInfo
from app.ui.si_theme import SiColors


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear(item.layout())


def _text(value: str, size=10, muted=False) -> QLabel:
    label = QLabel(value)
    label.setWordWrap(True)
    label.setFont(QFont("Microsoft YaHei UI", size,
                        QFont.Weight.Normal if muted else QFont.Weight.DemiBold))
    label.setStyleSheet(f"color: {SiColors.TEXT_MUTED if muted else SiColors.TEXT_PRIMARY};")
    return label


def _time(message: MessageInfo) -> str:
    if not message.timestamp:
        return "时间未知"
    try:
        return datetime.fromtimestamp(message.timestamp).strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError, OverflowError):
        return "时间未知"


class MessagesPage(QWidget):
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("shellRoot")
        self._messages: list[MessageInfo] = []
        self._category = "全部"
        self._selected_id: str | None = None
        root = QHBoxLayout(self)
        root.setContentsMargins(24, 10, 18, 16)
        root.setSpacing(16)
        for width, attr in ((None, "_left"), (275, "_right")):
            scroll = QScrollArea()
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            if width:
                scroll.setFixedWidth(width)
                self._right_scroll = scroll
            host = QWidget()
            host.setObjectName("shellRoot")
            layout = QVBoxLayout(host)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(12)
            setattr(self, attr, layout)
            scroll.setWidget(host)
            root.addWidget(scroll, 1 if width is None else 0)
        self._rebuild()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_right_scroll"):
            self._right_scroll.setVisible(self.width() >= 850)

    def set_messages(self, messages: list[MessageInfo]) -> None:
        self._messages = list(messages)
        if self._selected_id not in {m.msg_id for m in self._messages}:
            self._selected_id = self._messages[0].msg_id if self._messages else None
        self._rebuild()

    def retheme(self) -> None:
        self._rebuild()

    def _set_category(self, category: str) -> None:
        self._category = category
        self._rebuild()

    def _select(self, msg_id: str) -> None:
        self._selected_id = msg_id
        self._rebuild()
        if not self._right_scroll.isVisible():
            message = next((m for m in self._messages if m.msg_id == msg_id), None)
            if message is not None:
                dialog = QMessageBox(self)
                dialog.setWindowTitle(message.title or "消息")
                dialog.setTextFormat(Qt.TextFormat.PlainText)
                dialog.setText(message.body.strip() or "此消息没有正文。")
                dialog.exec()

    def _rebuild(self) -> None:
        _clear(self._left)
        _clear(self._right)
        categories = ["全部"] + sorted({m.category for m in self._messages if m.category})
        if self._category not in categories:
            self._category = "全部"
        head = QHBoxLayout()
        head.addWidget(_text("消息通知", 15))
        head.addStretch()
        head.addWidget(_text(f"近 24 小时 · {len(self._messages)} 条", 9, True))
        refresh = QPushButton("刷新")
        refresh.setObjectName("shellNeutralButton")
        refresh.clicked.connect(self.refresh_requested.emit)
        head.addWidget(refresh)
        self._left.addLayout(head)
        chips = QHBoxLayout()
        for category in categories:
            count = len(self._messages) if category == "全部" else sum(
                m.category == category for m in self._messages)
            button = QPushButton(f"{category}  {count}")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            chosen = category == self._category
            button.setStyleSheet(
                f"QPushButton {{ background: {SiColors.THEME if chosen else SiColors.CARD};"
                f" color: {SiColors.ON_THEME_TEXT if chosen else SiColors.TEXT_PRIMARY};"
                " border: none; border-radius: 14px; padding: 7px 12px; }}")
            button.clicked.connect(lambda _=False, c=category: self._set_category(c))
            chips.addWidget(button)
        chips.addStretch()
        self._left.addLayout(chips)
        filtered = [m for m in self._messages
                    if self._category == "全部" or m.category == self._category]
        if filtered:
            for message in filtered:
                self._left.addWidget(self._row(message))
        else:
            empty = QFrame()
            empty.setObjectName("homeSectionCard")
            empty.setMinimumHeight(260)
            lay = QVBoxLayout(empty)
            lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon = QLabel()
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setPixmap(qta.icon("mdi.bell-outline", color=SiColors.THEME).pixmap(32, 32))
            lay.addWidget(icon)
            line = _text("暂无消息")
            line.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(line)
            line = _text("设备告警与通知会出现在这里", 9, True)
            line.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(line)
            self._left.addWidget(empty)
        self._left.addStretch()
        selected = next((m for m in self._messages if m.msg_id == self._selected_id), None)
        self._right.addWidget(self._detail(selected))
        self._right.addStretch()

    def _row(self, message: MessageInfo) -> QWidget:
        card = QFrame()
        card.setObjectName("homeSectionCard")
        if message.msg_id == self._selected_id:
            card.setStyleSheet(f"QFrame#homeSectionCard {{ border: 2px solid {SiColors.THEME};"
                               " border-radius: 14px; }}")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        icon = QLabel()
        icon.setPixmap(qta.icon("mdi.bell-outline", color=SiColors.THEME).pixmap(24, 24))
        lay.addWidget(icon)
        col = QVBoxLayout()
        col.addWidget(_text(message.title or "通知", 11))
        if message.body.strip():
            preview = message.body.strip().replace("\n", " ")[:100]
            col.addWidget(_text(preview, 9, True))
        col.addWidget(_text(_time(message), 8, True))
        lay.addLayout(col, 1)
        button = QPushButton("查看")
        button.setObjectName("shellNeutralButton")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda: self._select(message.msg_id))
        lay.addWidget(button)
        return card

    def _detail(self, message: MessageInfo | None) -> QWidget:
        card = QFrame()
        card.setObjectName("homeSectionCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 18, 16, 18)
        lay.setSpacing(12)
        lay.addWidget(_text("消息详情", 13))
        if message is None:
            lay.addWidget(_text("选择一条消息查看内容。", 9, True))
            return card
        lay.addWidget(_text(message.title or "通知", 13))
        lay.addWidget(_text(_time(message), 9, True))
        if message.category:
            lay.addWidget(_text(f"分类：{message.category}", 9, True))
        lay.addWidget(_text(message.body.strip() or "此消息没有正文。", 10,
                            not bool(message.body.strip())))
        lay.addSpacing(10)
        lay.addWidget(_text("关联设备", 10))
        lay.addWidget(_text("当前消息接口未提供关联设备标识。", 9, True))
        return card
