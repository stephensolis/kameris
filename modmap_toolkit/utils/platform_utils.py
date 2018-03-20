from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import platform


def platform_name():
    if platform.system() == 'Windows':
        return 'windows'
    elif platform.system() == 'Linux':
        return 'linux'
    elif platform.system() == 'Darwin':
        return 'mac'
    else:
        return 'unknown'
