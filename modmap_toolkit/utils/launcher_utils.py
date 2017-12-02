from __future__ import absolute_import, division, unicode_literals

from distutils import spawn
import os
import platform
import psutil
from six.moves import input
import subprocess
import sys


def name_matches_process_or_parents(proc, name):
    """Returns whether the given name is the name of the given psutil.Process
    or any of its parents."""

    if proc is None:
        return False
    elif proc.name() == name:
        return True
    elif proc.parent() is not None and proc.pid == proc.parent().pid:
        return False
    else:
        return name_matches_process_or_parents(proc.parent(), name)


def maybe_running_in_shell():
    """Returns whether the current program might be running in an interactive
    shell.
    If unsure, will return True."""

    proc = psutil.Process()
    if platform.system() == 'Windows':
        return not name_matches_process_or_parents(proc, 'explorer.exe')
    else:
        return sys.stdout.isatty()


def spawn_shell(message=''):
    """Attempt to launch an independent interactive shell in the current
    directory, or pause if not possible.
    In either case, the given message will be printed for the user.

    WARNING: the message should not be from untrusted input, since it could be
    used to perform a shell injection.
    Also, double and single quotes in the message may cause issues."""

    win_echo_command = ' && '.join('echo ' + l if l.strip() else 'echo.'
                                   for l in message.splitlines())
    unix_echo_command = '; '.join(map(
        lambda l: "echo '{}'".format(l),
        message.splitlines()
    ))

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
        no_shell_message = """
        {0} is a command-line program, do not double-click it again!
        Type your command in this prompt below.

        If you are not sure what to do, type {0} --help on Windows
        or ./{0} --help on macOS/Linux.
        """.format(os.path.basename(sys.argv[0]))

    if not maybe_running_in_shell():
        spawn_shell(no_shell_message)
        sys.exit(1)
