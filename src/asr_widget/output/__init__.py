import platform

_system = platform.system()

if _system == "Darwin":
    from asr_widget.output.keystroke_mac import KeystrokeInjector
elif _system == "Windows":
    from asr_widget.output.keystroke_win import KeystrokeInjector
else:
    from asr_widget.output.keystroke import KeystrokeInjector

__all__ = ["KeystrokeInjector"]
