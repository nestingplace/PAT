import uasyncio as asyncio
from machine import UART, Pin

class DFPlayer:
    START_BYTE = 0x7E
    VERSION = 0xFF
    COMMAND_LENGTH = 0x06
    END_BYTE = 0xEF

    def __init__(self, uart_id=0, tx_pin_id=0, rx_pin_id=1, volume=80):
        self.uart = UART(uart_id, baudrate=9600, tx=Pin(tx_pin_id), rx=Pin(rx_pin_id))
        self.volume_level = volume
        asyncio.create_task(self.volume(self.volume_level))

    async def send_cmd(self, command, param1=0, param2=0):
        buffer = bytearray(10)
        buffer[0] = self.START_BYTE
        buffer[1] = self.VERSION
        buffer[2] = self.COMMAND_LENGTH
        buffer[3] = command
        buffer[4] = 0x00
        buffer[5] = param1
        buffer[6] = param2
        checksum = -(self.VERSION + self.COMMAND_LENGTH + command + buffer[4] + param1 + param2) & 0xFFFF
        buffer[7] = (checksum >> 8) & 0xFF
        buffer[8] = checksum & 0xFF
        buffer[9] = self.END_BYTE
        self.uart.write(buffer)
        await asyncio.sleep_ms(50)

    async def play(self, folder, file):
        folder = int(folder)
        file = int(file)
        await self.send_cmd(0x0F, folder, file)

    async def volume(self, volume):
        self.volume_level = max(0, min(volume, 30))
        await self.send_cmd(0x06, 0x00, self.volume_level)

    async def stop(self):
        await self.send_cmd(0x16)

    async def pause(self):
        await self.send_cmd(0x0E)

    async def resume(self):
        await self.send_cmd(0x0D)

    async def is_playing(self):
        self.uart.write(b'\x7E\xFF\x06\x42\x00\x00\x00\xFE\xBA\xEF')
        await asyncio.sleep_ms(10)
        return self.uart.any()
