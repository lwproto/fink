from typing import Optional, Tuple
import struct
import logging


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(f"[{name}] %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


class Fink:
    """
    Fink protocol implementation - ultra-light discrete protocol for IoT.

    Frame structure (fink-o-gram):
        [Magic: 1B][Flags: 1B][Length: 1B][Payload: 0-255B][CRC: 1B]
    """

    FLAG_URGENT = 0x01
    FLAG_REQUIRE_ACK = 0x02
    FLAG_ACK = 0x04

    def __init__(self):
        """
        Initialize Fink protocol instance.

        The magic byte is calculated using the "Together" method:
        CRC-8/ROHC of the "PROTOCOL/version" ASCII string.
        For FINK/1, magic = 0xDB.
        """

        self.protocol = "FINK/1"
        self.magic = self._crc8_rohc(self.protocol.encode("ascii"))  # "Together" method
        self.logger = get_logger("Fink")

    @staticmethod
    def _crc8_rohc(input_data: bytes) -> int:
        """
        Compute CRC-8/ROHC checksum.

        This is the reference implementation of the CRC-8/ROHC algorithm
        used by the "Together" method to generate the magic byte.

        Args:
            input_data: Bytes to checksum.

        Returns:
            8-bit CRC value.
        """

        poly = 0x07
        crc = 0xFF

        def reflect(b: int) -> int:
            r = 0
            for i in range(8):
                if b & (1 << i):
                    r |= 1 << (7 - i)
            return r

        for byte in input_data:
            byte = reflect(byte)
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ poly) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
        return reflect(crc)

    def pack(self, payload: bytes, flags: int = 0) -> Optional[bytes]:
        """
        Pack payload into a Fink frame (fink-o-gram).

        Frame structure:
            [Magic: 1B][Flags: 1B][Length: 1B][Payload: 0-255B][CRC: 1B]

        Flags bitmask:
            - Bit 0: URGENT
            - Bit 1: REQUIRE_ACK
            - Bit 2: ACK
            - Bits 3-7: Reserved (must be 0)

        Args:
            payload: User data (max 255 bytes).
            flags: Frame flags (default: 0).

        Returns:
            Packed frame as bytes, or None if payload exceeds 255 bytes.
        """

        if len(payload) > 255:
            self.logger.error(f"Payload is too long: {len(payload)} > 255!")
            return None

        else:
            header = struct.pack(">BBB", self.magic, flags, len(payload))
            without_crc = header + payload
            crc = self._crc8_rohc(without_crc)
            packet = without_crc + struct.pack(">B", crc)
            self.logger.debug(f"Packed frame: {packet.hex().upper()}")
            return packet

    def unpack(self, packet: bytes) -> Optional[Tuple[bytes, int]]:
        """
        Unpack a Fink frame (fink-o-gram) into payload and flags.

        Performs validation:
            1. Minimum frame size (4 bytes).
            2. Magic byte match.
            3. Length field consistency.
            4. CRC-8/ROHC checksum verification.

        Args:
            packet: Raw frame bytes.

        Returns:
            Tuple of (payload, flags) if valid, None otherwise.
        """

        if len(packet) < 4:
            self.logger.debug("Packet too short.")
            return None

        expected_magic, flags, length = struct.unpack(">BBB", packet[:3])

        if expected_magic != self.magic:
            self.logger.warning(
                f"Magic mismatch. Expected {hex(self.magic)}, got {hex(expected_magic)}"
            )
            return None

        if length > 255 or len(packet) != 4 + length:
            self.logger.warning("Invalid length field or packet size.")
            return None

        payload = packet[3 : 3 + length]
        received_crc = packet[3 + length]
        calculated_crc = self._crc8_rohc(packet[: 3 + length])

        if calculated_crc != received_crc:
            self.logger.warning(
                f"CRC mismatch. Expected {hex(calculated_crc)}, got {hex(received_crc)}"
            )
            return None

        self.logger.debug("Frame validated successfully.")
        return payload, flags


if __name__ == "__main__":
    fink = Fink()

    # TEST 1: normal
    print(" TEST 1: Normal ".center(50, "="))
    frame = fink.pack(b"Don't turn a matchstick into a multicooker!")
    if frame:
        payload, flags = fink.unpack(frame)
        print(f"OK: {payload.decode()}\n")

    # TEST 2: payload = 255 bytes
    print(" TEST 2: Length of Payload = 255 ".center(50, "="))
    payload_255 = b"A" * 255
    frame = fink.pack(payload_255)
    if frame:
        print(f"OK: 255 bytes packed\n")

    # TEST 3: payload = 256 bytes (will return None)
    print(" TEST 3: Overflow ".center(50, "="))
    payload_256 = b"B" * 256
    frame = fink.pack(payload_256)
    if frame is None:
        print("OK: 256 bytes rejected")
