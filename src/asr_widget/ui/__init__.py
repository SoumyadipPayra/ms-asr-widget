import platform

if platform.system() == "Darwin":
    from asr_widget.ui.widget_mac import FloatingWidget
    from asr_widget.ui.statusbar_mac import StatusBarItem
else:
    from asr_widget.ui.widget import FloatingWidget
    from asr_widget.ui.statusbar import StatusBarItem

__all__ = ["FloatingWidget", "StatusBarItem"]
