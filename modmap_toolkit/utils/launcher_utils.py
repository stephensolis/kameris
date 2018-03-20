from __future__ import (
    absolute_import, division, print_function, unicode_literals)

from distutils import spawn
import os
import platform
import psutil
from six.moves import input
import subprocess
import sys
import textwrap


def names_match_process_or_parents(proc, names):
    """Returns whether any of the given names are the name of the given
    psutil.Process or any of its parents."""

    if proc is None:
        return False
    elif any(name == proc.name().lower() for name in names):
        return True
    elif proc.parent() is not None and proc.pid == proc.parent().pid:
        return False
    else:
        return names_match_process_or_parents(proc.parent(), names)


def maybe_running_in_shell():
    """Returns whether the current program might be running in an interactive
    shell.
    If unsure, will return True."""

    proc = psutil.Process()
    if platform.system() == 'Windows':
        return not names_match_process_or_parents(proc, ['explorer.exe'])
    else:
        return True


def spawn_shell(message=''):
    """Attempt to launch an independent interactive shell in the current
    directory, or pause if not possible.
    In either case, the given message will be printed for the user.

    WARNING: the message should not be from untrusted input, since it could be
    used to perform a shell injection.
    Also, double and single quotes in the message may cause issues."""

    win_echo_command = ' && '.join('echo ' + l if l.strip() else 'echo.'
                                   for l in message.splitlines())
    unix_echo_command = '; '.join("echo '{}'".format(l)
                                  for l in message.splitlines())

    if platform.system() == 'Windows':
        subprocess.Popen('start cmd.exe /k "{}"'.format(win_echo_command),
                         shell=True)
    elif platform.system() == 'Darwin':
        subprocess.Popen([
            'osascript', '-e',
            'tell app "Terminal" to do script "{}"'.format(unix_echo_command)
        ])
    elif spawn.find_executable('x-terminal-emulator'):
        subprocess.Popen([
            'x-terminal-emulator', '-e',
            'bash -c "{}; $SHELL"'.format(unix_echo_command)
        ])
    else:
        print(message)
        print("I couldn't detect how to open a terminal, please do it "
              "yourself.")
        input('Press any key to continue...')


def ensure_running_in_shell(no_shell_message=None):
    """If the current program is probably not running in an interactive shell,
    opens an interactive shell with the given message and exits the program.
    If no message is given, prints a generic one telling the user not to
    double-click the program.

    WARNING: the message should not be from untrusted input, since it could be
    used to perform a shell injection."""

    if no_shell_message is None:
        if platform.system() == 'Windows':
            command_line = '{0} --help'
        else:
            command_line = './{0} --help'
        no_shell_message = textwrap.dedent(("""
            {0} is a command-line program, do not double-click it again!
            Type your command in this prompt below.

            If you are not sure what to do, type """ + command_line).format(
                os.path.basename(sys.argv[0])))

    if not maybe_running_in_shell():
        spawn_shell(no_shell_message)
        sys.exit(1)
