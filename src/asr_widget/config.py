from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 12):
    import tomllib
else:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]


@dataclass
class GatewayConfig:
    url: str = "ws://localhost:8765"


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    chunk_duration_ms: int = 100
    device: str | None = None

    @property
    def chunk_samples(self) -> int:
        return int(self.sample_rate * self.chunk_duration_ms / 1000)

    @property
    def chunk_bytes(self) -> int:
        return self.chunk_samples * 2  # 16-bit = 2 bytes per sample


@dataclass
class HotkeyConfig:
    combination: str = "<cmd>+<shift>+<space>"
    mode: str = "toggle"  # "toggle" or "push_to_talk"


@dataclass
class UIConfig:
    size: int = 44
    opacity: float = 0.9


@dataclass
class AppConfig:
    gateway: GatewayConfig = field(default_factory=GatewayConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    ui: UIConfig = field(default_factory=UIConfig)


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load configuration from TOML file, env vars, and defaults.

    Search order for config file:
      1. Explicit path argument
      2. ASR_WIDGET_CONFIG env var
      3. ./config.toml (next to the running script)
      4. ~/.config/asr-widget/config.toml
    """
    if path is None:
        path = os.environ.get("ASR_WIDGET_CONFIG")

    candidates: list[Path] = []
    if path is not None:
        candidates.append(Path(path))

    # Platform-specific config directory (written by setup wizard)
    if platform.system() == "Windows":
        _appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        candidates.append(_appdata / "asr-widget" / "config.toml")
    elif platform.system() == "Darwin":
        candidates.append(Path.home() / "Library" / "Application Support" / "asr-widget" / "config.toml")
    else:
        _xdg = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        candidates.append(_xdg / "asr-widget" / "config.toml")

    candidates.append(Path.cwd() / "config.toml")
    candidates.append(Path(__file__).resolve().parent.parent.parent / "config.toml")
    candidates.append(Path.home() / ".config" / "asr-widget" / "config.toml")

    data: dict = {}
    for candidate in candidates:
        if candidate.is_file():
            with open(candidate, "rb") as f:
                data = tomllib.load(f)
            break

    # Env var overrides
    gw_url = os.environ.get("ASR_WIDGET_GATEWAY_URL")

    gw = data.get("gateway", {})
    audio = data.get("audio", {})
    hk = data.get("hotkey", {})
    ui = data.get("ui", {})

    device_raw = audio.get("device")
    device = device_raw if device_raw else None

    return AppConfig(
        gateway=GatewayConfig(
            url=gw_url or gw.get("url", "ws://localhost:8765"),
        ),
        audio=AudioConfig(
            sample_rate=audio.get("sample_rate", 16000),
            chunk_duration_ms=audio.get("chunk_duration_ms", 100),
            device=device,
        ),
        hotkey=HotkeyConfig(
            combination=hk.get("combination", "<cmd>+<shift>+<space>"),
            mode=hk.get("mode", "toggle"),
        ),
        ui=UIConfig(
            size=ui.get("size", 44),
            opacity=ui.get("opacity", 0.9),
        ),
    )
