import argparse as ap

from src.app import AppController


def parse_args() -> ap.Namespace:
    parser = ap.ArgumentParser(
        prog='eTRM Measure Summary Tool',
        description='Creates a summary of one or more measures.')

    parser.add_argument('-t', '--token',
        metavar='token',
        type=str,
        help='eTRM authorization token (API key)')

    return parser.parse_args()


def main():
    args = parse_args()
    token: str | None = getattr(args, 'token', None)
    if token != None:
        token = 'Token ' + token
    main_app = AppController()
    main_app.run(auth_token=token)


if __name__ == '__main__':
    main()
