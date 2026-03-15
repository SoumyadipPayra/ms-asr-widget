from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_USER_CONFIG = Path.home() / ".config" / "asr-widget" / "config.toml"


def is_first_run() -> bool:
    return not _USER_CONFIG.exists()


def show_setup_dialog(default_url: str = "ws://localhost:8765") -> str | None:
    """Show first-run setup dialog asking for the gateway URL.

    Returns the URL entered by the user, or None if they cancelled.
    """
    from AppKit import NSAlert, NSTextField
    from Foundation import NSMakeRect

    from AppKit import NSApplication
    NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    alert = NSAlert.alloc().init()
    alert.setMessageText_("Welcome to ASR Widget")
    alert.setInformativeText_(
        "Enter the WebSocket URL of your ASR gateway server.\n"
        "Leave as default if running locally."
    )
    alert.addButtonWithTitle_("Connect")
    alert.addButtonWithTitle_("Cancel")

    text_field = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 300, 24))
    text_field.setStringValue_(default_url)
    alert.setAccessoryView_(text_field)
    alert.layout()
    text_field.selectText_(None)

    response = alert.runModal()
    if response == 1000:  # NSAlertFirstButtonReturn
        return str(text_field.stringValue()).strip() or default_url
    return None


def save_user_config(gateway_url: str) -> None:
    """Write the user config to ~/.config/asr-widget/config.toml."""
    _USER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    _USER_CONFIG.write_text(
        f'[gateway]\nurl = "{gateway_url}"\n'
    )
    logger.info("Saved user config: %s", _USER_CONFIG)
