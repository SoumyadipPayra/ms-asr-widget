import platform

if platform.system() == "Darwin":
    from asr_widget.output.keystroke_mac import KeystrokeInjector
else:
    from asr_widget.output.keystroke import KeystrokeInjector

__all__ = ["KeystrokeInjector"]
