# SPDX-License-Identifier: GPL-3.0-or-later
# MiHome-Windows: 米家设备的 Windows 桌面控制端
"""首页聚合：时段问候、状态 chips、房间分组、关注项与常用设备启发式。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.core.models import DeviceInfo

# 启发式关键字（model / name 小写包含匹配）
_LIGHT_KEYS = ("light", "lamp", "bulb", "switch", "plug", "outlet", "夜灯", "灯")
_AC_KEYS = ("aircondition", "air-condition", "ac", "空调", "thermostat", "heater")
_CURTAIN_KEYS = ("curtain", "moto", "shade", "窗帘", "百叶")
_MEDIA_KEYS = ("tv", "television", "projector", "soundbar", "mediaplayer", "电视", "投影")
_SENSOR_KEYS = ("sensor", "magnet", "motion", "烟雾", "漏水", "传感器")


def greeting_text(now: datetime | None = None) -> str:
    hour = (now or datetime.now()).hour
    if hour < 6:
        return "夜深了"
    if hour < 12:
        return "早上好"
    if hour < 18:
        return "下午好"
    return "晚上好"


def classify_device(device: DeviceInfo) -> str:
    blob = f"{device.model} {device.name}".lower()
    if any(k in blob for k in _LIGHT_KEYS):
        return "light"
    if any(k in blob for k in _AC_KEYS):
        return "climate"
    if any(k in blob for k in _CURTAIN_KEYS):
        return "curtain"
    if any(k in blob for k in _MEDIA_KEYS):
        return "media"
    if any(k in blob for k in _SENSOR_KEYS):
        return "sensor"
    return "other"


@dataclass
class RoomSummary:
    name: str
    devices: list[DeviceInfo] = field(default_factory=list)

    @property
    def online(self) -> int:
        return sum(1 for d in self.devices if d.online)

    @property
    def offline(self) -> int:
        return len(self.devices) - self.online

    def metric_texts(self, metrics: dict[str, str | None]) -> list[str]:
        texts: list[str] = []
        for d in self.devices:
            text = metrics.get(d.did)
            if text:
                texts.append(text)
        return texts


def group_rooms(devices: list[DeviceInfo]) -> list[RoomSummary]:
    order: list[str] = []
    buckets: dict[str, list[DeviceInfo]] = {}
    for d in devices:
        room = d.room_name or "未分配"
        if room not in buckets:
            buckets[room] = []
            order.append(room)
        buckets[room].append(d)
    order.sort(key=lambda n: (n == "未分配", n))
    return [RoomSummary(name=n, devices=buckets[n]) for n in order]


def status_chips(
    devices: list[DeviceInfo],
    known_power: dict[str, bool | None],
) -> list[tuple[str, str, int]]:
    """返回 (icon_key, label, count)，count<=0 的不入列。"""
    online = [d for d in devices if d.online]
    lights = acs = curtains = 0
    for d in online:
        kind = classify_device(d)
        on = known_power.get(d.did) is True
        if kind == "light" and on:
            lights += 1
        elif kind == "climate" and on:
            acs += 1
        elif kind == "curtain" and on:
            curtains += 1
    chips: list[tuple[str, str, int]] = []
    if lights:
        chips.append(("light", "盏灯亮着", lights))
    if acs:
        chips.append(("climate", "台空调已开启", acs))
    if curtains:
        chips.append(("curtain", "台窗帘设备已开启", curtains))
    chips.append(("device", "台设备在线", len(online)))
    return chips


@dataclass
class AttentionItem:
    did: str
    title: str
    detail: str
    severity: str  # offline | battery | warn


def build_attention(
    devices: list[DeviceInfo],
    known_power: dict[str, bool | None],
    low_battery: set[str] | None = None,
    consumables: list | None = None,
) -> list[AttentionItem]:
    items: list[AttentionItem] = []
    for d in devices:
        if not d.online:
            items.append(AttentionItem(
                did=d.did,
                title=f"{d.name} 已离线",
                detail=d.room_name or d.home_name,
                severity="offline",
            ))
    for did in sorted(low_battery or ()):
        dev = next((d for d in devices if d.did == did), None)
        if dev is not None:
            items.append(AttentionItem(
                did=dev.did,
                title=f"{dev.name} 电量偏低",
                detail=dev.room_name or "请尽快更换电池",
                severity="battery",
            ))
    for c in consumables or []:
        value = str(getattr(c, "value", "") or "")
        desc = getattr(c, "description", "耗材")
        name = getattr(c, "device_name", "设备")
        did = getattr(c, "did", "")
        try:
            if value.strip().endswith("%") and float(value.strip("%")) > 20:
                continue
        except ValueError:
            pass
        items.append(AttentionItem(
            did=did,
            title=f"{name} {desc}",
            detail=value or "耗材需关注",
            severity="battery",
        ))
    return items


def pick_common_devices(
    devices: list[DeviceInfo],
    known_power: dict[str, bool | None],
    tray_dids: list[str] | None = None,
    limit: int = 6,
) -> list[DeviceInfo]:
    by_did = {d.did: d for d in devices}
    if tray_dids:
        picked = [by_did[d] for d in tray_dids if d in by_did]
        if picked:
            return picked[:limit]
    # 启发式：优先可开关的在线设备，再按类型权重
    weight = {"light": 0, "climate": 1, "curtain": 2, "media": 3, "other": 4, "sensor": 5}
    scored: list[tuple[int, int, DeviceInfo]] = []
    for d in devices:
        if not d.online:
            continue
        kind = classify_device(d)
        has_power = known_power.get(d.did) is not None
        scored.append((0 if has_power else 1, weight.get(kind, 9), d))
    scored.sort(key=lambda t: (t[0], t[1], t[2].name))
    return [d for _, _, d in scored[:limit]]
