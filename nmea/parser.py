"""
Handle parsing of string sentences into Python types.

The `parser.parse()` function takes a single line NMEA sentence and passes it to the
approriate `sentences.Sentence` subclass.

The rest of the module consists mostly of utility functions.
"""

import datetime
from typing import Dict, List, Optional, Type

from . import sentences, checksum


SENTENCE_TYPES: Dict[str, Type[sentences.Sentence]] = {
    '$GNGGA': sentences.GGA,
    '$GPGGA': sentences.GGA,
    '$GNGSA': sentences.GSA,
    '$GPGSA': sentences.GSA,
    '$GLGSV': sentences.GSV,
    '$GPGSV': sentences.GSV,
    '$GNRMC': sentences.RMC,
    '$GPRMC': sentences.RMC,
    '$GNTXT': sentences.TXT,
}


class UnknownSentence(ValueError):
    pass


def parse(sentence: str) -> sentences.Sentence:
    """
    Take full NMEA sentence and attempt to parse it using the correct sentence.
    """
    checksum.verify(sentence)
    fields = sentence_split(sentence)

    # Find matching sentence dataclass
    nmea = fields[0]
    try:
        sentence_type = SENTENCE_TYPES[nmea]
    except KeyError as e:
        message = f"Unknown NMEA sentence: {e}"
        raise UnknownSentence(message) from None

    # Build and return dataclass
    data = sentence_type.from_fields(fields)
    return data


def parse_altitude(value: str, units: str) -> Optional[float]:
    """
    Calculate altitude value in metres.
    """
    if not value:
        return None
    altitude = float(value)
    units = units.upper()
    if units == 'M':
        return altitude
    else:
        raise ValueError(f'Unknown altitude units: {units!r}')


def parse_date(value: str) -> Optional[datetime.date]:
    """
    Parse NMEA date string into a Python `datetime.date` object.

    Raises:
        ValueError:
            If given value does not match the required format.

    Returns:
        Date object or None
    """
    if not value:
        return None

    if len(value) != 6:
        raise ValueError("NMEA date string must be 6-characters long")

    # Unexpected Y2k-like nonsense! Roll-over is 1980, as per NMEA standard.
    year = int(value[4:]) + 1900
    if year < 1980:
        year += 100

    try:
        date = datetime.date(year, int(value[2:4]), int(value[:2]))
    except ValueError:
        raise ValueError(f"Invalid NMEA date string: {value!r}") from None

    return date


def parse_declination(value: str, direction: str) -> Optional[float]:
    degrees = parse_float(value)
    if degrees is None:
        return None

    direction = direction.upper()
    if direction == 'E':
        return degrees
    elif direction == 'W':
        return -degrees
    else:
        raise ValueError(f"Declination has bad direction: {direction!r}")


def parse_degrees(value: str) -> float:
    """
    Parse degrees in NMEA format to decimal degrees.

    The format is '[D]DDMM.MMMM' - an integer number of degrees, then a real
    number of minutes. There are a variable number of digits to either side
    of the decimal point.

    Args:
        value:
            A string from a NMEA message.

    Returns:
        The degrees as a single floating point number, rounded to six digits.
    """
    if not value:
        raise ValueError(f"Cannot parse degrees, empty value given: {value!r}")
    first, _, fraction = value.partition('.')
    value = first[:-2]
    degrees = float(value) if value else 0
    minutes = float(f"{first[-2:]}.{fraction}")
    degrees += minutes / 60
    return round(degrees, 6)


def parse_float(value: str) -> Optional[float]:
    if not value:
        return None
    return float(value)


def parse_latitude(latitude: str, direction: str) -> Optional[float]:
    """
    Parse the NMEA latitude to a floating-point number.

    Raises:
        ValueError:
            Bad direction or latitide values.

    Returns:
        Latitude or float.
    """
    if not latitude and not direction:
        return None
    degrees = parse_degrees(latitude)
    direction = direction.upper()
    if direction == 'N':
        return degrees
    elif direction == 'S':
        return -degrees
    else:
        raise ValueError(f"Latitude has bad direction: {direction!r}")


def parse_longitude(longitude: str, direction: str) -> Optional[float]:
    """
    Parse the NMEA longitude to a floating-point number.

    Raises:
        ValueError:
            Bad direction or longitude values.

    Returns:
        Longitude.
    """
    if not longitude and not direction:
        return None
    degrees = parse_degrees(longitude)
    direction = direction.upper()
    if direction == 'E':
        return degrees
    elif direction == 'W':
        return -degrees
    else:
        raise ValueError(f"Longitude has bad direction: {direction!r}")


def parse_speed(value: str) -> Optional[float]:
    """
    Parse speed, converting to meters per second.

    Args:
        value:
            Speed in nautical knots.

    Returns:
        Speed in metres per second, rounded to six digits.
    """
    speed = parse_float(value)
    if speed is None:
        return None
    # Nautical mile is exactly 1852 metres
    ms = speed * (1852/3600)
    return round(ms, 6)


def parse_time(value: str) -> Optional[datetime.time]:
    """
    Parse time in HHMMSS.SSS format.
    """
    if not value:
        return None

    if len(value) < 6:
        raise ValueError("NMEA time string must be at least 6-characters long")

    hours = int(value[:2])
    minutes = int(value[2:4])
    seconds = int(value[4:6])
    microseconds = int(f"{value[7:]:0<6}")
    return datetime.time(hours, minutes, seconds, microseconds)


def sentence_split(sentence: str) -> List[str]:
    """
    Split sentence into fields.
    """
    # Drop checksum
    sentence, _, _ = sentence.partition('*')
    return sentence.split(',')
