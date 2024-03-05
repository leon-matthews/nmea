
import argparse
import logging
from pathlib import Path
import sys
import time
from typing import Iterator, List

from . import parser, utils


logger = logging.getLogger(__name__)


def argparse_existing_file(string: str) -> Path:
    """
    An `argparse` type to convert string to a `Path` object.

    Raises `argparse.ArgumentTypeError` if path does not exist.
    """
    path = Path(string).expanduser().resolve()
    error = None
    if not path.exists():
        error = f"File does not exist: {path}"
    if not path.is_file():
        error = f"Path is not a file: {path}"

    if error is not None:
        raise argparse.ArgumentTypeError(error)
    return path


class Command:
    """
    Read and translate NMEA log files.
    """
    def __init__(self, args: List[str]):
        self.options = self.parse_options(args)
        self.setup_logging()

    def parse_options(self, args: List[str]) -> argparse.Namespace:
        script_name = Path(__file__).parent.name
        parser = argparse.ArgumentParser(description='Parse NMEA log files', prog=script_name)
        parser.add_argument(
            'file',
            metavar='FILE',
            type=argparse_existing_file,
            help="NMEA log file. May be compressed.")
        options = parser.parse_args(args)
        return options

    def main(self) -> int:
        start = time.perf_counter()
        count = 0
        print('[')
        for line in self.readlines():
            try:
                data = parser.parse(line)
                count += 1
                print(data.to_json(), end=',\n')
            except parser.UnknownSentence as e:
                logger.debug(e)
        print(']')

        elapsed = (time.perf_counter() - start) * 1000
        logger.info(f"Parsed {count:,} sentences in {elapsed:.1f}ms")
        return 0

    def readlines(self) -> Iterator[str]:
        path = self.options.file
        logger.debug(f"Reading lines from: {path}")
        num_lines = 0
        with utils.magic_open(path) as fp:
            for line in fp:
                num_lines += 1
                yield line.strip()
        logger.debug(f"Read {num_lines:,} lines from: {path.name}")

    def setup_logging(self) -> None:
        level = logging.DEBUG
        logging.basicConfig(
            force=True,
            format="{levelname}: {message}",
            level=level,
            style='{',
        )


if __name__ == '__main__':
    command = Command(sys.argv[1:])
    retval = command.main()
    sys.exit(retval)
