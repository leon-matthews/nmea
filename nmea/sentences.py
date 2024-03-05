"""
Provides a Python dataclass subclass for every NMEA sentence of interest.
"""
from __future__ import annotations      # Allow forward references for return types

import dataclasses
from dataclasses import dataclass
import datetime
import json
from typing import List, Optional

from . import parser


@dataclass
class Satellite:
    """
    Satellite metadata (from GSV message).
    """
    id_number: int                      # ID number of this satellite
    elevation: float                    # Satellite elevation (-90 to 90 degrees)
    azimuth: float                      # Azimuth to true north (0 to 359 degrees)
    snr: Optional[float]                # Signal-to-noise ratio (dB)

    @classmethod
    def from_fields(cls, fields: List[str]) -> Satellite:
        return cls(
            id_number=int(fields[0]),
            elevation=float(fields[1]),
            azimuth=float(fields[2]),
            snr=parser.parse_float(fields[3]),
        )


class Sentence:
    """
    Python dataclass for a single NMEA sentence.

    A one-to-one relationship exists between a line of text and its matching
    dataclass object.  Compound messages (like GSV) can be combined at a higher
    level of code.
    """
    @classmethod
    def from_fields(cls, fields: List[str]) -> Sentence:
        raise NotImplementedError()

    def to_json(self) -> str:
        raw = dataclasses.asdict(self)
        raw['_type'] = self.__class__.__name__
        data = {}
        for key, value in raw.items():
            if isinstance(value, datetime.date):
                value = value.isoformat()
            elif isinstance(value, datetime.time):
                value = value.isoformat()
            data[key] = value
        return json.dumps(data, sort_keys=True, indent=4)


@dataclass
class GGA(Sentence):
    """
    Fix information.
    """
    time: Optional[datetime.time]
    latitude: Optional[float]
    longitude: Optional[float]
    position_fix: int
    satellites_used: int
    hdop: Optional[float]
    altitude_msl: Optional[float]       # Mean sea level
    altitude_hae: Optional[float]       # Height above ellipsoid (geoid)
    differential_age: str
    differential_reference: str

    @classmethod
    def from_fields(cls, fields: List[str]) -> GGA:
        if 'GGA' not in fields[0]:
            raise ValueError(f"$GxGGA not in first field, found: {fields[0]!r}")

        return cls(
            time=parser.parse_time(fields[1]),
            latitude=parser.parse_latitude(fields[2], fields[3]),
            longitude=parser.parse_longitude(fields[4], fields[5]),
            position_fix=int(fields[6]),
            satellites_used=int(fields[7]),
            hdop=parser.parse_float(fields[8]),
            altitude_msl=parser.parse_altitude(fields[9], fields[10]),
            altitude_hae=parser.parse_altitude(fields[11], fields[12]),
            differential_age=fields[13],
            differential_reference=fields[14],
        )


@dataclass
class GSA(Sentence):
    """
    Dilution of precision (DOP), and active satellites.
    """
    mode: str                           # Manual 'M' or automatic 'A'
    fix: int                            # 1: not available, 2: 2D, 3: 3D
    ids: List[int]                      # IDs (1-32: GPS, 33-64: SBAS, 64+: GLONASS)
    pdop: Optional[float]               # PDOP: Position of DOP, 3D dillution of precision
    hdop: Optional[float]               # HDOP: Horizontal of DOP
    vdop: Optional[float]               # VDOP: Vertical of DOP

    @classmethod
    def from_fields(cls,  fields: List[str]) -> GSA:
        if 'GSA' not in fields[0]:
            raise ValueError(f"$GxGSA not in first field, found: {fields[0]!r}")

        ids = [int(n) for n in fields[3:-3] if n]
        return cls(
            mode=fields[1],
            fix=int(fields[2]),
            ids=ids,
            pdop=parser.parse_float(fields[-3]),
            hdop=parser.parse_float(fields[-2]),
            vdop=parser.parse_float(fields[-1]),
        )


@dataclass
class GSV(Sentence):
    """
    Satellites in view.
    """
    messages_total: int                 # How many GSV messages total
    message_number: int                 # Index of this message (1-based)
    satellites_total: int               # Total number of satellites in view
    satellites: List[Satellite]

    @classmethod
    def from_fields(cls,  fields: List[str]) -> GSV:
        if 'GSV' not in fields[0]:
            raise ValueError(f"$GxGSV not in first field, found: {fields[0]!r}")

        # Message
        messages_total = int(fields[1])
        message_number = int(fields[2])
        satellites_total = int(fields[3])
        remaining_fields = fields[4:]

        # Satellites
        satellites = []
        NUM_FIELDS = 4
        for i in range(0, len(remaining_fields), NUM_FIELDS):
            satellite_fields = remaining_fields[i:i+NUM_FIELDS]
            if len(satellite_fields) != NUM_FIELDS:
                raise ValueError(
                    f"Wrong number of satellite fields in sentence. {NUM_FIELDS} fields "
                    f"expected, found: {satellite_fields}"
                )
            satellite = Satellite.from_fields(satellite_fields)
            satellites.append(satellite)

        return cls(
            messages_total=messages_total,
            message_number=message_number,
            satellites_total=satellites_total,
            satellites=satellites,
        )


@dataclass
class RMC(Sentence):
    """
    Recommended minimum data.
    """
    time: Optional[datetime.time]
    status: str
    latitude: Optional[float]
    longitude: Optional[float]
    speed: Optional[float]              # Metres per second
    course: Optional[float]             # Degrees
    date: Optional[datetime.date]
    declination: Optional[float]        # Magnetic declination, degrees east.

    @classmethod
    def from_fields(cls, fields: List[str]) -> RMC:
        if 'RMC' not in fields[0]:
            raise ValueError(f"$GxRMC not in first field, found: {fields[0]!r}")
        return cls(
            time=parser.parse_time(fields[1]),
            status=fields[2],
            latitude=parser.parse_latitude(fields[3], fields[4]),
            longitude=parser.parse_longitude(fields[5], fields[6]),
            speed=parser.parse_speed(fields[7]),
            course=parser.parse_float(fields[8]),
            date=parser.parse_date(fields[9]),
            declination=parser.parse_declination(fields[10], fields[11]),
        )

    @property
    def speed_kph(self) -> Optional[float]:
        """
        Convert speed from metres per second, to common kilometres per hour.
        """
        if self.speed is None:
            return None
        return self.speed * 3.6

    @property
    def datetime(self) -> Optional[datetime.datetime]:
        """
        Build full datetime object and add UTC timezone.

        Returns:
            Timezone-aware `datetime.datetime` object.
        """
        if (self.date is None) or (self.time is None):
            return None

        date = datetime.datetime(
            year=self.date.year,
            month=self.date.month,
            day=self.date.day,
            hour=self.time.hour,
            minute=self.time.minute,
            second=self.time.second,
            microsecond=self.time.microsecond,
            tzinfo=datetime.timezone.utc,
        )
        return date


@dataclass
class TXT(Sentence):
    """
    Text transmission
    """
    sentence_id: int
    sentence_number: int
    sentences_total: int
    message: str

    @classmethod
    def from_fields(cls, fields: List[str]) -> TXT:
        if 'TXT' not in fields[0]:
            raise ValueError(f"$GxTXT not in first field, found: {fields[0]!r}")

        return cls(
            sentence_id=int(fields[1]),
            sentence_number=int(fields[2]),
            sentences_total=int(fields[3]),
            message=fields[4],
        )
