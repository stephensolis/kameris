from __future__ import absolute_import, division, unicode_literals


import argparse
import os
import shutil
import subprocess
import platform


def mkdir_p(dir):
    try:
        os.makedirs(dir)
    except OSError:
        pass


def symlink(src, dest):
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


def argparse_check_dir(dir):
    if not os.path.isdir(dir):
        raise argparse.ArgumentTypeError(dir + ' is not a directory')
    else:
        return dir
