# SPDX-License-Identifier: GPL-3.0-or-later
# MiHome-Windows: 米家设备的 Windows 桌面控制端
"""Open-Meteo 天气与空气质量（免 API Key，仅出网 GET）。"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

_GEO = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST = "https://api.open-meteo.com/v1/forecast"
_AIR = "https://air-quality-api.open-meteo.com/v1/air-quality"

# WMO weather interpretation codes → 中文
_WMO = {
    0: "晴",
    1: "晴间多云",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "冻雾",
    51: "毛毛雨",
    53: "毛毛雨",
    55: "毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "阵雨",
    81: "阵雨",
    82: "强阵雨",
    85: "阵雪",
    86: "阵雪",
    95: "雷雨",
    96: "雷雨冰雹",
    99: "雷雨冰雹",
}


@dataclass
class WeatherSnapshot:
    city: str
    temperature: float | None
    weather_text: str
    aqi: int | None
    aqi_text: str


def _aqi_label(aqi: float | None) -> str:
    if aqi is None:
        return ""
    a = float(aqi)
    if a <= 50:
        return "优"
    if a <= 100:
        return "良"
    if a <= 150:
        return "轻度污染"
    if a <= 200:
        return "中度污染"
    if a <= 300:
        return "重度污染"
    return "严重污染"


def geocode_city(name: str, timeout: float = 8.0) -> tuple[float, float, str] | None:
    """城市名 → (lat, lon, 展示名)。"""
    name = (name or "").strip()
    if not name:
        return None
    try:
        r = requests.get(
            _GEO,
            params={"name": name, "count": 1, "language": "zh", "format": "json"},
            timeout=timeout,
        )
        r.raise_for_status()
        results = r.json().get("results") or []
        if not results:
            return None
        item = results[0]
        label = item.get("name") or name
        admin = item.get("admin1") or ""
        if admin and admin != label:
            label = f"{label}"
        return float(item["latitude"]), float(item["longitude"]), str(label)
    except Exception as exc:
        logger.warning("地理编码失败 %s: %s", name, exc)
        return None


def fetch_weather(city: str, timeout: float = 10.0) -> WeatherSnapshot | None:
    """按城市名拉当前气温、天气现象与 AQI。失败返回 None。"""
    geo = geocode_city(city, timeout=timeout)
    if geo is None:
        return None
    lat, lon, label = geo
    try:
        w = requests.get(
            _FORECAST,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weather_code",
                "timezone": "auto",
            },
            timeout=timeout,
        )
        w.raise_for_status()
        cur = w.json().get("current") or {}
        temp = cur.get("temperature_2m")
        code = cur.get("weather_code")
        weather_text = _WMO.get(int(code) if code is not None else -1, "天气")

        aqi = None
        aqi_text = ""
        try:
            a = requests.get(
                _AIR,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "us_aqi,pm2_5",
                    "timezone": "auto",
                },
                timeout=timeout,
            )
            a.raise_for_status()
            acur = a.json().get("current") or {}
            if acur.get("us_aqi") is not None:
                aqi = int(float(acur["us_aqi"]))
            elif acur.get("pm2_5") is not None:
                # 无 AQI 时用 PM2.5 粗映射（示意）
                pm = float(acur["pm2_5"])
                aqi = int(min(300, pm * 2))
            aqi_text = _aqi_label(aqi)
        except Exception as exc:
            logger.debug("空气质量获取失败: %s", exc)

        return WeatherSnapshot(
            city=label,
            temperature=float(temp) if temp is not None else None,
            weather_text=weather_text,
            aqi=aqi,
            aqi_text=aqi_text,
        )
    except Exception as exc:
        logger.warning("天气获取失败 %s: %s", city, exc)
        return None
