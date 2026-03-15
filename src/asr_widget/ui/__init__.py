import platform

_system = platform.system()

if _system == "Darwin":
    from asr_widget.ui.widget_mac import FloatingWidget
    from asr_widget.ui.statusbar_mac import StatusBarItem
elif _system == "Windows":
    from asr_widget.ui.widget_win import FloatingWidget
    from asr_widget.ui.statusbar_win import StatusBarItem
else:
    from asr_widget.ui.widget import FloatingWidget
    from asr_widget.ui.statusbar import StatusBarItem

__all__ = ["FloatingWidget", "StatusBarItem"]
