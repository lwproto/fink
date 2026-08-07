import struct
from typing import Optional, Tuple
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
    def __init__(self):
        self.protocol = "FINK/1"
        # "Together" method
        self.magic = self._crc8_rohc(self.protocol.encode("ascii"))
        self.logger = get_logger("Fink")

    @staticmethod
    def _crc8_rohc(input_data: bytes) -> int:
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

    def pack(self, payload: bytes, flags: int = 0) -> bytes:
        header = struct.pack(">BBB", self.magic, flags, len(payload))
        without_crc = header + payload
        crc = self._crc8_rohc(without_crc)
        packet = without_crc + struct.pack(">B", crc)
        self.logger.debug(f"Packed frame: {packet.hex().upper()}")
        return packet

    def unpack(self, packet: bytes) -> Optional[Tuple[bytes, int]]:
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
    frame = fink.pack("Don't turn a matchstick into a multicooker!".encode("utf-8"))
    print(f"{frame[:3].hex(' ').upper()} {frame[3:-1].hex().upper()} {frame[-1].to_bytes().hex()}")

    payload, flags = fink.unpack(frame)
    print(payload.decode("utf-8"))