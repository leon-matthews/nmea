
import bz2
from contextlib import contextmanager
import gzip
import lzma
from pathlib import Path
from typing import Iterator, IO


@contextmanager
def magic_open(
    path: Path,
    mode: str = 'rt',
    encoding: str = 'utf-8',
    errors: str = 'strict',
    newline: Optional[str] = None,
) -> Iterator[IO[str]]:
    """
    Open plain or compressed files transparently as context manager.

    Recognises BZ2, GZ, and XZ compressed files. Falls back
    to uncompressed opening if file extension not recognised.

    For example::

        >>> with magic_open(path) as fp:
        ...    do_something()

    Args:
        path: File path to compressed or plain file
        mode: File open mode.
        encoding: Text file encoding.
        errors: How encoding errors should be handled.

    Return:
        A file handle
    """
    # Pick a open function
    path = Path(path)
    extension = path.suffix.lower()
    open_functions = {
        '.bz2': bz2.open,
        '.gz': gzip.open,
        '.xz': lzma.open,
    }
    open_function = open_functions.get(extension, open)

    # Context manager
    try:
        fp = open_function(path, mode, encoding=encoding, errors=errors, newline=newline)
        yield fp
    finally:
        fp.close()
