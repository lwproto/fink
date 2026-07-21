import struct
from typing import Optional, Tuple

class Fink:
    def __init__(self):
        self.protocol = "FINK/1"
        self.magic = self._crc8_rohc(self.protocol.encode("utf-8"))  # "Together" method

    def _crc8_rohc(self, input: bytes) -> int:
        poly = 0x07
        crc = 0xFF

        def reflect(b: int) -> int:
            r = 0
            for i in range(8):
                if b & (1 << i):
                    r |= 1 << (7 - i)
            return r

        for byte in input:
            byte = reflect(byte)
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ poly) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF

        return reflect(crc)

    def _pack(self, payload: bytes, flags: int = 0) -> bytes:
        header = struct.pack(">BBB", self.magic, flags, len(payload))
        without_crc = header + payload
        crc = self._crc8_rohc(without_crc)
        packet = without_crc + struct.pack(">B", crc)
        return packet

    def _unpack(self, packet: bytes) -> Optional[Tuple[bytes, int]]:
        excepted_magic = packet[0]

        if excepted_magic != self.magic:
            return

        flags, length = struct.unpack(">BB", packet[1:3])

        payload = packet[3 : length + 3]
        excepted_crc = packet[3 + length]
        crc = self._crc8_rohc(packet[: 3 + length])

        if crc != excepted_crc:
            return

        return payload, flags


if __name__ == "__main__":
    fink = Fink()
    frame = fink._pack("".encode("utf-8"))
    print(f"{frame[:3].hex(' ').upper()} {frame[3:-1].hex().upper()} {frame[-1].to_bytes().hex()}")

    payload, flags = fink._unpack(frame)
    print(payload.decode("utf-8"))
