
import datetime
from unittest import TestCase

from nmea import parser, sentences


class ParseTest(TestCase):
    """
    End-to-end parsing of various sentence types.
    """
    sentences = {
        'GGA': "$GNGGA,031921.542,3653.0286,S,17441.8568,E,0,00,,-26.2,M,26.2,M,,0000*6D",
        'GSA': "$GNGSA,A,3,19,14,02,20,06,03,24,12,17,,,,1.48,0.81,1.24*14",
        'GSV': "$GPGSV,3,1,10,26,66,061,,03,58,266,,22,52,324,,16,49,014,*78",
        'RMC': "$GPRMC,010432.00,A,3653.0835,S,17441.9076,E,"
               "26.99784,240.241,240521,19.9,E*4C",
        'TXT': "$GNTXT,01,01,02,ROM CORE 3.01 (107888)*2B",
    }

    def test_parse(self) -> None:
        for type_string, line in self.sentences.items():
            data = parser.parse(line)
            self.assertIsInstance(data, sentences.Sentence)
            self.assertEqual(type_string, data.__class__.__name__)

    def test_unknown_sentence_type(self) -> None:
        line = "$GNGXG,01,01,02,ROM CORE 3.01 (107888)*2B"
        message = r"Unknown NMEA sentence: '\$GNGXG'"
        with self.assertRaisesRegex(parser.UnknownSentence, message):
            parser.parse(line)


class ParseAltitudeTest(TestCase):
    def test_valid_altitude(self) -> None:
        altitude = parser.parse_altitude('45', 'M')
        self.assertEqual(altitude, 45.0)

    def test_empty_altitude(self) -> None:
        altitude = parser.parse_altitude('', 'M')
        self.assertEqual(altitude, None)

    def test_unknown_unit(self) -> None:
        message = "Unknown altitude units: 'Y'"
        with self.assertRaisesRegex(ValueError, message):
            parser.parse_altitude('325.34', 'Y')


class ParseDateTest(TestCase):
    def test_parser_date(self) -> None:
        self.assertEqual(parser.parse_date('240521'), datetime.date(2021, 5, 24))

    def test_parser_date_empty(self) -> None:
        self.assertEqual(parser.parse_date(''), None)

    def test_parser_date_bad_length(self) -> None:
        message = 'NMEA date string must be 6-characters long'

        # Too short
        with self.assertRaisesRegex(ValueError, message):
            parser.parse_date('24052')

        # Too long
        with self.assertRaisesRegex(ValueError, message):
            parser.parse_date('24052021')

    def test_parser_date_bad_characters(self) -> None:
        message = "Invalid NMEA date string: '1Dec21'"
        with self.assertRaisesRegex(ValueError, message):
            parser.parse_date('1Dec21')

    def test_parser_date_bad_values(self) -> None:
        message = "Invalid NMEA date string: '999999'"
        with self.assertRaisesRegex(ValueError, message):
            parser.parse_date('999999')

    def test_parser_date_y2k(self) -> None:
        """
        Test handling of (silly) 2-digit year value.
        """
        self.assertEqual(parser.parse_date('010178'), datetime.date(2078, 1, 1))
        self.assertEqual(parser.parse_date('010179'), datetime.date(2079, 1, 1))
        self.assertEqual(parser.parse_date('010180'), datetime.date(1980, 1, 1))
        self.assertEqual(parser.parse_date('010181'), datetime.date(1981, 1, 1))


class ParseDeclinationTest(TestCase):
    def test_parse_declination_east(self) -> None:
        # Upper case
        declination = parser.parse_declination('12.2', 'E')
        assert declination is not None
        self.assertAlmostEqual(declination, 12.2)

        # Lower-case
        declination = parser.parse_declination('12.2', 'e')
        assert declination is not None
        self.assertAlmostEqual(declination, 12.2)

    def test_parse_declination_west(self) -> None:
        # Upper case
        declination = parser.parse_declination('12.2', 'W')
        assert declination is not None
        self.assertAlmostEqual(declination, -12.2)

        # Lower-case
        declination = parser.parse_declination('12.2', 'w')
        assert declination is not None
        self.assertAlmostEqual(declination, -12.2)

    def test_parse_declination_empty(self) -> None:
        self.assertIs(parser.parse_declination('', ''), None)
        self.assertIs(parser.parse_declination('', 'W'), None)

    def test_parse_declination_bad_direction(self) -> None:
        message = "Declination has bad direction: 'Z'"
        with self.assertRaisesRegex(ValueError, message):
            parser.parse_declination('123', 'Z')


class ParseDegreesTest(TestCase):
    def test_three_digits(self) -> None:
        # Auckland Longitude 174° 44.4' East
        degrees = parser.parse_degrees('17444.400')
        self.assertEqual(degrees, 174.740000)

    def test_two_digits(self) -> None:
        # Auckland Latitude 36° 50.433333' South
        degrees = parser.parse_degrees('3650.433333')
        self.assertEqual(degrees, 36.840556)

    def test_one_digit(self) -> None:
        # Paris 2° 21.132' East
        degrees = parser.parse_degrees('221.132')
        self.assertEqual(degrees, 2.3522)

    def test_zero_digits(self) -> None:
        # London 0° 7.668' West
        degrees = parser.parse_degrees('7.668')
        self.assertEqual(degrees, 0.1278)

    def test_empty(self) -> None:
        message = r"Cannot parse degrees, empty value given: ''"
        with self.assertRaisesRegex(ValueError, message):
            parser.parse_degrees('')


class ParseFloatTest(TestCase):
    def test_parse_float(self) -> None:
        self.assertEqual(parser.parse_float('42'), 42.0)

    def test_parse_float_empty(self) -> None:
        self.assertEqual(parser.parse_float(''), None)


class ParseLatitudeTest(TestCase):
    def test_parse_latitude_empty(self) -> None:
        latitude = parser.parse_latitude('', '')
        self.assertTrue(latitude is None)

    def test_parse_latitude_north(self) -> None:
        # Winnipeg, Canada 49° 53.706' North
        latitude = parser.parse_latitude('4953.706', 'N')
        self.assertEqual(latitude, 49.8951)

    def test_parse_latitude_south(self) -> None:
        # Auckland, New Zealand 36° 50.433333' South
        latitude = parser.parse_latitude('3650.433333', 's')       # Lower-case okay
        self.assertEqual(latitude, -36.840556)

    def test_parse_latitude_bad_direction(self) -> None:
        with self.assertRaises(ValueError) as cm:
            parser.parse_latitude('3650.433333', 'A')
        self.assertEqual(str(cm.exception), "Latitude has bad direction: 'A'")


class ParseLongitudeTest(TestCase):
    def test_parse_latitude_empty(self) -> None:
        longitude = parser.parse_longitude('', '')
        self.assertTrue(longitude is None)

    def test_parse_longitude_west(self) -> None:
        # Winnipeg, Canada 97° 8.304' W
        longitude = parser.parse_longitude('9708.304', 'W')
        self.assertEqual(longitude, -97.1384)

    def test_parse_longitude_east(self) -> None:
        # Auckland Longitude 174° 44.4' East
        longitude = parser.parse_longitude('17444.400', 'E')
        self.assertEqual(longitude, 174.740000)

    def test_parse_longitude_bad_direction(self) -> None:
        with self.assertRaises(ValueError) as cm:
            parser.parse_longitude('3650.433333', 'Z')
        self.assertEqual(str(cm.exception), "Longitude has bad direction: 'Z'")


class ParseSpeedTest(TestCase):
    def test_parse_speed(self) -> None:
        speed = parser.parse_speed('8')
        assert speed is not None
        self.assertAlmostEqual(speed, 4.1155556, places=6)

    def test_parse_speed_empty(self) -> None:
        self.assertEqual(parser.parse_speed(''), None)


class ParseTimeTest(TestCase):
    def test_parse_time(self) -> None:
        time = parser.parse_time('161229.487')
        self.assertEqual(time, datetime.time(16, 12, 29, 487000))

    def test_parse_time_no_microseconds(self) -> None:
        time = parser.parse_time('161229')
        self.assertEqual(time, datetime.time(16, 12, 29, 0))

    def test_parse_time_too_short(self) -> None:
        message = "NMEA time string must be at least 6-characters long"
        with self.assertRaisesRegex(ValueError, message):
            parser.parse_time('16122')

    def test_parse_time_empty(self) -> None:
        time = parser.parse_time('')
        self.assertIs(time, None)


class SentenceSplitTest(TestCase):
    def test_sentence_split(self) -> None:
        sentence = (
            "$GPRMC,231312.20,A,3653.0882,S,17441.9026,E,0.2624,328.856,230521,19.9,E*4A"
        )
        parts = parser.sentence_split(sentence)
        expected = [
            '$GPRMC',
            '231312.20',
            'A',
            '3653.0882',
            'S',
            '17441.9026',
            'E',
            '0.2624',
            '328.856',
            '230521',
            '19.9',
            'E'
        ]
        self.assertEqual(parts, expected)
