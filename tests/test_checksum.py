
from unittest import TestCase

from nmea import checksum


class ChecksumAddTest(TestCase):
    def test_already_exists(self) -> None:
        sentence = "$GPVTG,2.95,T,,M,16.1,N,29.8,K*5B"
        with self.assertRaises(ValueError) as cm:
            checksum.add(sentence)

        message = "Sentence already has a checksum: '$GPVTG,2.95,T,,M,16.1,N,29.8,K*5B'"
        self.assertEqual(str(cm.exception), message)

    def test_checksum_add(self) -> None:
        sentence = "$GPVTG,2.95,T,,M,16.1,N,29.8,K"
        sentence2 = checksum.add(sentence)
        self.assertEqual(sentence2, "$GPVTG,2.95,T,,M,16.1,N,29.8,K*5B")


class ChecksumCalculateTest(TestCase):
    def test_checksum_calculate(self) -> None:
        sentence = '$GPGLL,3554.923,N,08202.503,W,054937.591,V*31'  # 0x31 == 49
        calculated = checksum.calculate(sentence)
        self.assertIsInstance(calculated, int)
        self.assertGreaterEqual(calculated, 0)
        self.assertLessEqual(calculated, 255)
        self.assertEqual(calculated, 49)

    def test_not_existing(self) -> None:
        sentence = '$GPGLL,3554.923,N,08202.503,W,054937.591,V'
        calculated = checksum.calculate(sentence)
        self.assertEqual(calculated, 49)


class ChecksumVerifyTest(TestCase):
    def test_valid(self) -> None:
        sentence = '$GPGGA,055044.591,3554.916,N,08202.532,W,0,00,,,M,,M,,*59'
        self.assertTrue(checksum.verify(sentence))

    def test_invalid(self) -> None:
        sentence = '$GPGGA,055044.591,3554.916,N,08202.532,W,0,00,,,M,,M,,*FF'
        with self.assertRaises(ValueError) as cm:
            checksum.verify(sentence)

        message = "Checksum in sentence does not match that calculated: 0xFF != 0x59"
        self.assertEqual(str(cm.exception), message)

    def test_missing(self) -> None:
        sentence = '$GPGGA,055044.591,3554.916,N,08202.532,W,0,00,,,M,,M,,'
        with self.assertRaises(ValueError) as cm:
            checksum.verify(sentence)

        message = (
            "Given sentence has no checksum: "
            "'$GPGGA,055044.591,3554.916,N,08202.532,W,0,00,,,M,,M,,'"
        )
        self.assertEqual(str(cm.exception), message)
