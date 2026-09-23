# SPDX-License-Identifier: GPL-3.0-or-later
"""主窗口五页路由与共用壳层的离屏回归。"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from app.core import cache as device_cache
from app.core import settings_store
from app.core.models import DeviceInfo, MessageInfo, SceneInfo
from app.ui import si_theme
from app.ui.main_window import MainWindow


def main() -> None:
    app = QApplication.instance() or QApplication([])
    if not QFontDatabase.families():
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/msyh.ttc")
    si_theme.set_theme("light")
    app.setStyleSheet(si_theme.build_qss())
    original_shell_getter = settings_store.get_home_shell_enabled
    original_cache_save = device_cache.save
    settings_store.get_home_shell_enabled = lambda: True
    device_cache.save = lambda *args, **kwargs: None
    try:
        win = MainWindow()
        win._clamp_to_screen = lambda: None
        win._default_size_applied = True
        win._all_devices = [
            DeviceInfo("test-light", "客厅主灯", "xiaomi.light.v1", "我的家", "客厅", True),
            DeviceInfo("test-sensor", "温湿度传感器", "xiaomi.sensor.v1", "我的家", "客厅", True),
            DeviceInfo("other-home", "其他家庭的灯", "xiaomi.light.v1", "另一个家", "客厅", True),
        ]
        win._known_power = {"test-light": True}
        win._metrics = {"test-sensor": "23.4°C  51%"}
        win._homes = ["我的家"]
        win._current_home = "我的家"
        win._scenes_loaded = True
        win.load_messages = lambda: None
        win._scenes_page.set_scenes([
            SceneInfo("test-scene", "回家模式", "test-home", "我的家")])
        win._messages_page.set_messages([
            MessageInfo("test-message", "设备提醒", "测试正文", 0, "设备")])
        win._message_count = 1
        win._update_shell_panels()
        assert len(win._home_page._devices) == 2
        assert len(win._rooms_page._devices) == 2
        assert len(win._devices_page._devices) == 2
        win.resize(1440, 900)
        win.show()
        app.processEvents()
        win._open_default_room_panel()
        app.processEvents()
        out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
        if out:
            out.mkdir(parents=True, exist_ok=True)
        for route, index in (("home", 0), ("rooms", 1), ("devices", 2),
                             ("scenes", 3), ("messages", 7)):
            win._on_shell_navigate(route)
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()
            assert win._content_stack.currentIndex() == index
            assert win._shell_header._title.text()
            if route == "home":
                assert win._room_panel.isVisible()
            else:
                assert not win._room_panel.isVisible()
            if out:
                assert win.grab().save(str(out / f"{route}.png"))
        win._all_devices = []
        win._force_quit = True
        win.close()
        print("[OK] 主窗口五页路由与共用标题栏")
    finally:
        settings_store.get_home_shell_enabled = original_shell_getter
        device_cache.save = original_cache_save


if __name__ == "__main__":
    main()
