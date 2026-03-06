import sys

if sys.platform == "win32":
    from .win32 import WindowsSpeedBadge as SpeedBadge
elif sys.platform == "darwin":
    from .mac import MacSpeedBadge as SpeedBadge
else:
    from .linux import LinuxSpeedBadge as SpeedBadge

