import argparse


def main():
    ...


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='create new')
    parser.add_argument('--clean-logs',
                        action='store_true',
                        help='delete logs in arb_logs/ before starting')

    args = parser.parse_args()

    main()