import sys


def get_sys_platform() -> str:
    platform = sys.platform.lower()
    if platform.startswith('win'):
        return 'windows'

    elif platform.startswith('darwin'):
        return 'macOS'

    else:
        return platform


def is_windows() -> bool:
    return sys.platform.lower().startswith('win')
