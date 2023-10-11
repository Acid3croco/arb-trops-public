import argparse
import subprocess

from pathlib import Path


def execute_command(command):
    executable = '/bin/bash'
    process = subprocess.Popen(command, shell=True, executable=executable)
    process.wait()


def manage_package(package_name, action):
    """
    Manage package.
    """
    print()
    print('----------------------------------------')
    print('Processing package: {}'.format(package_name))
    print('----------------------------------------')
    if action == 'install':
        command = f'pip3 install -e {package_name}'
        print(command)
        execute_command(command)
    elif action == 'uninstall':
        command = f'pip3 uninstall {package_name}'
        print(command)
        execute_command(command)
    else:
        print('Invalid action')
        exit(1)


def process_action(action, packages_list, root_dir=None):
    """
    Execute action for packages.
    """
    if len(packages_list) == 0:
        root_dir = root_dir if root_dir else '.'
        root_dir = Path(root_dir)
        print(root_dir)
        packages_list = [x for x in root_dir.iterdir() if x.is_dir()]

    for package in packages_list:
        manage_package(package, action)


def main():
    parser = argparse.ArgumentParser(description='manage packages')

    parser.add_argument('-a',
                        '--action',
                        type=str,
                        choices=['install', 'uninstall'],
                        required=True)
    parser.add_argument('-d',
                        '--dir',
                        type=str,
                        help='root directory of packages')
    parser.add_argument('-p',
                        '--packages',
                        type=str,
                        nargs='*',
                        help='packages to install',
                        default=[])

    args = parser.parse_args()

    process_action(args.action, args.packages, args.dir)


if __name__ == '__main__':
    main()
