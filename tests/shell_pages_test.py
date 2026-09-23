# SPDX-License-Identifier: GPL-3.0-or-later
"""新版五页离屏渲染与基本数据状态回归。

运行：QT_QPA_PLATFORM=offscreen python -m tests.shell_pages_test [截图目录]
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QLabel

from app.core.models import DeviceInfo, MessageInfo, SceneInfo
from app.ui import si_theme
from app.ui.shell.devices_page import DevicesPage
from app.ui.shell.home_page import HomePage
from app.ui.shell.messages_page import MessagesPage
from app.ui.shell.rooms_page import RoomsPage
from app.ui.shell.scenes_page import ScenesPage


def _labels(widget) -> str:
    return "\n".join(label.text() for label in widget.findChildren(QLabel))


def main() -> None:
    app = QApplication.instance() or QApplication([])
    # Windows 的 Qt offscreen 平台不枚举系统字体，显式加载用于截图。
    if not QFontDatabase.families():
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/msyh.ttc")
    si_theme.set_theme("light")
    app.setStyleSheet(si_theme.build_qss())
    devices = [
        DeviceInfo("light-1", "客厅主灯", "xiaomi.light.v1", "我的家", "客厅", True),
        DeviceInfo("light-2", "落地灯", "xiaomi.lamp.v1", "我的家", "客厅", True),
        DeviceInfo("ac-1", "客厅空调", "xiaomi.aircondition.v1", "我的家", "客厅", True),
        DeviceInfo("curtain-1", "客厅窗帘", "xiaomi.curtain.v1", "我的家", "客厅", True),
        DeviceInfo("sensor-1", "温湿度传感器", "xiaomi.sensor.v1", "我的家", "客厅", True),
        DeviceInfo("light-3", "卧室吸顶灯", "xiaomi.light.v1", "我的家", "主卧", False),
        DeviceInfo("other-1", "书房插座", "xiaomi.plug.v1", "我的家", "书房", True),
    ]
    power = {"light-1": True, "light-2": False, "ac-1": True,
             "curtain-1": False, "light-3": None, "other-1": True}
    metrics = {"sensor-1": "23.4°C  51%"}
    pages = {
        "home": HomePage(),
        "rooms": RoomsPage(),
        "devices": DevicesPage(),
        "scenes": ScenesPage(),
        "messages": MessagesPage(),
    }
    pages["home"].update_data(devices, power, metrics)
    pages["rooms"].update_data(devices, power, metrics)
    pages["devices"].update_data(devices, power, metrics)
    pages["scenes"].set_scenes([
        SceneInfo("scene-1", "回家模式", "home-1", "我的家"),
        SceneInfo("scene-2", "观影时间", "home-1", "我的家"),
    ])
    pages["messages"].set_messages([
        MessageInfo("msg-1", "门锁提醒", "来自设备的真实消息正文", 0, "设备"),
    ])
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if out:
        out.mkdir(parents=True, exist_ok=True)
    for name, page in pages.items():
        page.resize(1200, 780)
        page.show()
        for _ in range(4):
            if page.layout():
                page.layout().activate()
            app.processEvents()
        if out:
            assert page.grab().save(str(out / f"{name}.png"))
        assert page.width() == 1200
        assert page.height() == 780
        page.hide()

    assert "暂无历史环境数据" in _labels(pages["rooms"])
    assert "当前接口不提供自动化规则列表" in _labels(pages["scenes"])
    assert "当前消息接口未提供关联设备标识" in _labels(pages["messages"])
    pages["rooms"].select_room("主卧")
    assert pages["rooms"]._selected_room == "主卧"
    pages["rooms"].select_room("客厅")
    pages["devices"]._search.setText("客厅主灯")
    assert "客厅主灯" in _labels(pages["devices"])
    pages["devices"]._search.clear()
    pages["devices"]._set_kind("传感器")
    assert pages["devices"]._kind == "传感器"
    pages["devices"]._set_kind("全部")
    pages["scenes"]._select("scene-2")
    assert pages["scenes"]._selected_id == "scene-2"
    pages["messages"]._set_category("设备")
    assert pages["messages"]._category == "设备"
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    si_theme.set_theme("dark")
    app.setStyleSheet(si_theme.build_qss())
    pages["home"].update_data(devices, power, metrics)
    pages["rooms"].update_data(devices, power, metrics)
    pages["devices"].update_data(devices, power, metrics)
    pages["scenes"].retheme()
    pages["messages"].retheme()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    if out:
        dark_out = out / "dark"
        dark_out.mkdir(parents=True, exist_ok=True)
        for name, page in pages.items():
            page.show()
            app.processEvents()
            assert page.grab().save(str(dark_out / f"{name}.png"))
            page.hide()
    if out:
        compact_out = out / "compact"
        compact_out.mkdir(parents=True, exist_ok=True)
    for name, page in pages.items():
        page.resize(528, 700)
        page.show()
        app.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        page.resize(528, 700)
        app.processEvents()
        assert page.width() == 528, f"{name}: {page.width()}"
        if hasattr(page, "_right_scroll"):
            assert not page._right_scroll.isVisible(), name
        if out:
            assert page.grab().save(str(compact_out / f"{name}.png"))
        page.hide()
    pages["scenes"].set_scenes([])
    pages["messages"].set_messages([])
    assert "暂无手动场景" in _labels(pages["scenes"])
    assert "暂无消息" in _labels(pages["messages"])
    print("[OK] 五页渲染、真实数据字段与空状态")
    for page in pages.values():
        page.close()
    app.quit()


if __name__ == "__main__":
    main()
