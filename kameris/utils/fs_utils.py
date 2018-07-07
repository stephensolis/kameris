from __future__ import absolute_import, division, unicode_literals


import os
import shutil
import subprocess
import platform


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError:
        pass


def symlink(src, dest):
    src = os.path.abspath(src)
    dest = os.path.abspath(dest)

    if platform.system() == 'Windows':
        if os.path.isdir(src):
            subprocess.check_output('mklink /j "{}" "{}"'.format(dest, src),
                                    shell=True)
        else:
            subprocess.check_output('mklink /h "{}" "{}"'.format(dest, src),
                                    shell=True)
    else:
        os.symlink(src, dest)


def cp_r(src, dest):
    if os.path.isdir(src):
        shutil.copytree(src, dest)
    else:
        shutil.copy(src, dest)
