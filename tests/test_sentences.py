
import dataclasses
import datetime
import textwrap
from typing import List
from unittest import TestCase

from nmea import sentences
from nmea import parser


class TestBaseSentence(TestCase):
    def test_from_fields_not_implemented(self) -> None:
        with self.assertRaises(NotImplementedError):
            sentences.Sentence.from_fields([])


class TestGGA(TestCase):
    """
    Test GGA (fix information) sentence handling.
    """
    expected = {
        'altitude_hae': 26.2,
        'altitude_msl': -26.2,
        'differential_age': '',
        'differential_reference': '0000',
        'hdop': None,
        'latitude': -36.88381,
        'longitude': 174.697613,
        'position_fix': 0,
        'satellites_used': 0,
        'time': datetime.time(3, 19, 21, 542000),
    }

    def test_parse_GNGGA(self) -> None:
        s = "$GNGGA,031921.542,3653.0286,S,17441.8568,E,0,00,,-26.2,M,26.2,M,,0000*6D"
        data = parser.parse(s)
        self.assertEqual(dataclasses.asdict(data), self.expected)

    def test_parse_GPGGA(self) -> None:
        s = "$GPGGA,031921.542,3653.0286,S,17441.8568,E,0,00,,-26.2,M,26.2,M,,0000*73"
        data = parser.parse(s)
        self.assertEqual(dataclasses.asdict(data), self.expected)

    def test_wrong_sentence_type(self) -> None:
        fields = parser.sentence_split(
            '$GPGSA,A,3,10,12,21,23,25,31,32,,,,,,1.6,0.9,1.3*3A'
        )
        with self.assertRaises(ValueError) as cm:
            sentences.GGA.from_fields(fields)
        self.assertEqual(str(cm.exception), "$GxGGA not in first field, found: '$GPGSA'")


class TestGSA(TestCase):
    """
    Test GSA (DOP, active satellites) sentence handling.
    """
    first = "$GNGSA,A,3,19,14,02,20,06,03,24,12,17,,,,1.48,0.81,1.24*14"
    second = "$GNGSA,A,3,82,80,73,,,,,,,,,,1.48,0.81,1.24*19"

    def test_parse_GNGSA_first(self) -> None:
        data = parser.parse(self.first)
        assert isinstance(data, sentences.GSA)
        self.check(data)
        self.assertEqual(data.ids, [19, 14, 2, 20, 6, 3, 24, 12, 17])

    def test_parse_GNGSA_second(self) -> None:
        data = parser.parse(self.second)
        assert isinstance(data, sentences.GSA)
        self.check(data)
        self.assertEqual(data.ids, [82, 80, 73])

    def check(self, data: sentences.GSA) -> None:
        self.assertEqual(data.mode, 'A')
        self.assertEqual(data.fix, 3)
        assert data.pdop is not None
        assert data.hdop is not None
        assert data.vdop is not None
        self.assertAlmostEqual(data.pdop, 1.48)
        self.assertAlmostEqual(data.hdop, 0.81)
        self.assertAlmostEqual(data.vdop, 1.24)

    def test_wrong_sentence_type(self) -> None:
        fields = parser.sentence_split("$GPGSV,3,3,10,01,05,306,,29,05,123,*77")
        with self.assertRaises(ValueError) as cm:
            sentences.GSA.from_fields(fields)
        self.assertEqual(str(cm.exception), "$GxGSA not in first field, found: '$GPGSV'")


class TestGSV(TestCase):
    """
    Test GSV (satellites in view) sentence handling.
    """
    # A complete group of three GSV sentences (see fields 2 and 3)
    group = (
        "$GPGSV,3,1,10,26,66,061,,03,58,266,,22,52,324,,16,49,014,*78",
        "$GPGSV,3,2,10,31,46,134,,04,38,229,,32,10,069,24,09,06,238,*76",
        "$GPGSV,3,3,10,01,05,306,,29,05,123,*77",
    )

    def test_parse_GPGSV(self) -> None:
        data = parser.parse(self.group[0])
        assert isinstance(data, sentences.GSV)

        # Message
        self.assertEqual(data.messages_total, 3)
        self.assertEqual(data.message_number, 1)
        self.assertEqual(data.satellites_total, 10)

        # Satellites
        self.assertEqual(data.satellites, [
            sentences.Satellite(id_number=26, elevation=66.0, azimuth=61.0, snr=None),
            sentences.Satellite(id_number=3, elevation=58.0, azimuth=266.0, snr=None),
            sentences.Satellite(id_number=22, elevation=52.0, azimuth=324.0, snr=None),
            sentences.Satellite(id_number=16, elevation=49.0, azimuth=14.0, snr=None),
        ])

    def test_wrong_number_satellite_fields(self) -> None:
        line = "$GPGSV,3,3,10,01,05,306,,29,05,*77"
        fields = parser.sentence_split(line)
        message = (
            r"Wrong number of satellite fields in sentence. 4 fields "
            r"expected, found: \['29', '05', ''\]")
        with self.assertRaisesRegex(ValueError, message):
            sentences.GSV.from_fields(fields)

    def test_wrong_sentence_type(self) -> None:
        fields = parser.sentence_split(
            '$GPGSA,A,3,10,12,21,23,25,31,32,,,,,,1.6,0.9,1.3*3A'
        )
        with self.assertRaises(ValueError) as cm:
            sentences.GSV.from_fields(fields)
        self.assertEqual(str(cm.exception), "$GxGSV not in first field, found: '$GPGSA'")


class TestRMC(TestCase):
    fields: List[str]
    line: str

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.line = (
            "$GPRMC,010432.00,A,3653.0835,S,17441.9076,E,"
            "26.99784,240.241,240521,19.9,E*4C"
        )
        cls.fields = parser.sentence_split(cls.line)

    def test_parse_GPRMC(self) -> None:
        rmc = sentences.RMC.from_fields(self.fields)
        assert rmc.course is not None
        self.assertAlmostEqual(rmc.course, 240.241, places=3)
        self.assertEqual(rmc.date, datetime.date(2021, 5, 24))
        assert rmc.declination is not None
        self.assertAlmostEqual(rmc.declination, 19.9, places=1)
        assert rmc.latitude is not None
        self.assertAlmostEqual(rmc.latitude, -36.884725, places=6)
        assert rmc.longitude is not None
        self.assertAlmostEqual(rmc.longitude, 174.69846, places=6)
        assert rmc.speed is not None
        self.assertAlmostEqual(rmc.speed, 13.888889, places=6)
        self.assertEqual(rmc.status, 'A')
        self.assertEqual(rmc.time, datetime.time(1, 4, 32))

    def test_property_speed_kmh(self) -> None:
        rmc = sentences.RMC.from_fields(self.fields)
        # For the benefit of mypy
        assert rmc.speed is not None
        assert rmc.speed_kph is not None
        self.assertAlmostEqual(rmc.speed, 13.888889, places=6)
        self.assertAlmostEqual(rmc.speed_kph, 50.0, places=6)

        # Deal with an empty value properly
        rmc.speed = None
        self.assertIs(rmc.speed_kph, None)

    def test_property_datetime(self) -> None:
        rmc = sentences.RMC.from_fields(self.fields)
        assert rmc.datetime is not None
        self.assertEqual(rmc.datetime.isoformat(), '2021-05-24T01:04:32+00:00')

    def test_property_datetime_incomplete(self) -> None:
        # Remove date field
        fields = self.fields.copy()
        fields[9] = ''
        rmc = sentences.RMC.from_fields(fields)
        self.assertIs(rmc.datetime, None)

    def test_to_json(self) -> None:
        data = parser.parse(self.line)
        string = data.to_json()
        expected = textwrap.dedent("""
        {
            "_type": "RMC",
            "course": 240.241,
            "date": "2021-05-24",
            "declination": 19.9,
            "latitude": -36.884725,
            "longitude": 174.69846,
            "speed": 13.888889,
            "status": "A",
            "time": "01:04:32"
        }
        """).strip()
        self.assertEqual(string, expected)

    def test_wrong_setence_type(self) -> None:
        fields = parser.sentence_split(
            '$GPGSA,A,3,10,12,21,23,25,31,32,,,,,,1.6,0.9,1.3*3A'
        )
        with self.assertRaises(ValueError) as cm:
            sentences.RMC.from_fields(fields)
        self.assertEqual(str(cm.exception), "$GxRMC not in first field, found: '$GPGSA'")


class TestTXT(TestCase):
    """
    Test TXT (text transmission) sentence handling.
    """
    line = "$GNTXT,01,01,02,ROM CORE 3.01 (107888)*2B"

    def test_parse_txt(self) -> None:
        data = parser.parse(self.line)
        assert isinstance(data, sentences.TXT)
        self.assertEqual(data.sentence_id, 1)
        self.assertEqual(data.sentence_number, 1)
        self.assertEqual(data.sentences_total, 2)
        self.assertEqual(data.message, "ROM CORE 3.01 (107888)")

    def test_wrong_sentence_type(self) -> None:
        fields = parser.sentence_split(
            '$GPGSA,A,3,10,12,21,23,25,31,32,,,,,,1.6,0.9,1.3*3A'
        )
        with self.assertRaises(ValueError) as cm:
            sentences.TXT.from_fields(fields)
        self.assertEqual(str(cm.exception), "$GxTXT not in first field, found: '$GPGSA'")
