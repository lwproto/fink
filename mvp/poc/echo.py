from typing import Optional, Tuple
import asyncio
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
    def __init__(self):
        self.protocol = "FINK/1"
        self.magic = self._crc8_rohc(self.protocol.encode("ascii"))  # "Together" method
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

    def pack(self, payload: bytes, flags: int = 0) -> Optional[bytes]:
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


class UDPTransport(asyncio.DatagramProtocol):
    def __init__(self, datagram_queue: asyncio.Queue):
        self.datagram_queue = datagram_queue
        self.transport = None
        self.logger = get_logger("UDPTransport")

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, datagram: bytes, addr: Tuple[str, int]):
        self.logger.debug(f"Received datagram from {addr}: {datagram.hex().upper()}")
        self.datagram_queue.put_nowait((datagram, addr))

    def error_received(self, exc):
        self.logger.error(f"Socket error: {exc}")


class Application:
    def __init__(self):
        self.fink = Fink()
        self.transport = None
        self.protocol = None
        self.datagram_queue = asyncio.Queue()
        self._processing_task = None
        self.logger = get_logger("Application")

    async def start(self):
        loop = asyncio.get_running_loop()

        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: UDPTransport(self.datagram_queue), local_addr=("127.0.0.1", 8000)
        )

        self._processing_task = asyncio.create_task(self._process_datagrams())

        self.logger.info(f"UDP server working on 127.0.0.1:8000")
        return self

    async def _process_datagrams(self):
        while True:
            try:
                datagram, addr = await self.datagram_queue.get()
                await self._handle_datagram(datagram, addr)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Failed to process datagram: {e}")

    async def _handle_datagram(self, datagram: bytes, addr: Tuple[str, int]):
        payload, flags = self.fink.unpack(datagram)
        if payload:
            try:
                message = payload.decode("utf-8")
                self.logger.debug(f"Received payload from {addr}: {message}")
            except UnicodeDecodeError:
                self.logger.debug(
                    f"Received binary payload from {addr}: {payload.hex()}"
                )
        else:
            self.logger.error(f"Failed to unpack frame from {addr}")

    def send(self, payload: bytes, addr: Tuple[str, int]):
        if self.transport:
            frame = self.fink.pack(payload=payload, flags=0)
            self.transport.sendto(frame, addr)
            self.logger.debug(f"Sent frame to {addr}: {frame.hex().upper()}")

    def close(self):
        if self._processing_task:
            self._processing_task.cancel()
        if self.transport:
            self.transport.close()


async def main():
    app = Application()

    try:
        await app.start()

        messages = [
            "Fink is a lightweight discrete protocol with minimal overhead.",
            "ONLY 4 BYTES!",
            "...and remember:",
            "Don't turn a matchstick into a multicooker!",
        ]

        for message in messages:
            print("\n" + f" {message} ".center(75, "="))
            app.send(message.encode("utf-8"), ("127.0.0.1", 8000))
            await asyncio.sleep(2)

        await asyncio.sleep(1)

    finally:
        app.close()


if __name__ == "__main__":
    asyncio.run(main())
