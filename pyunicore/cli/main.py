""" Main client class """

import platform
import sys

import pyunicore.cli.base
import pyunicore.cli.exec
import pyunicore.cli.io

_commands = {
    "cancel-job": pyunicore.cli.exec.CancelJob,
    "exec": pyunicore.cli.exec.Exec,
    "issue-token": pyunicore.cli.base.IssueToken,
    "list-jobs": pyunicore.cli.exec.ListJobs,
    "ls": pyunicore.cli.io.LS,
    "run": pyunicore.cli.exec.Run,
}


def get_command(name):
    return _commands.get(name)()


def show_version():
    print(
        "UNICORE Commandline Client (pyUNICORE) "
        "%s, https://www.unicore.eu" % pyunicore._version.get_versions().get("version", "n/a")
    )
    print("Python %s" % sys.version)
    print("OS: %s" % platform.platform())


def help():
    s = """UNICORE Commandline Client (pyUNICORE) %s, https://www.unicore.eu
Usage: unicore <command> [OPTIONS] <args>
The following commands are available:""" % pyunicore._version.get_versions().get(
        "version", "n/a"
    )
    print(s)
    for cmd in sorted(_commands):
        print(f" {cmd:20} - {get_command(cmd).get_description()}")
    print("Enter 'unicore <command> -h' for help on a particular command.")


def run(args):
    _help = ["help", "-h", "--help"]
    if len(args) < 1 or args[0] in _help:
        help()
        return
    _version = ["version", "-V", "--version"]
    if args[0] in _version:
        show_version()
        return

    command = None
    cmd = args[0]
    for k in _commands:
        if k.startswith(cmd):
            command = get_command(k)
            break
    if command is None:
        raise ValueError(f"No such command: {cmd}")
    command.run(args[1:])


def main():
    """
    Main entry point
    """
    run(sys.argv[1:])


if __name__ == "__main__":
    main()
