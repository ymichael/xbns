import argparse
import rateless_deluge
import time


def main(args):
    app = rateless_deluge.RatelessDeluge.create_and_run_application()

    # Seed data.
    seed_data = args.file.read()
    args.file.close()
    app.new_version(args.version, seed_data)

    while True:
        time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Deluge Application')
    parser.add_argument('--file', '-f', type=argparse.FileType(), required=True,
                        help='File to seed as the initial version of the data.')
    parser.add_argument('--version', '-v', type=int, default=1,
                        help='The version number of the seed file.')
    args = parser.parse_args()
    main(args)
