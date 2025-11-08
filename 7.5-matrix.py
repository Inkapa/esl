#!/usr/bin/python
# -*- coding:utf-8 -*-
"""
Matrix Animation for Waveshare 7.5" E-ink Display
Standalone version with integrated drivers
"""

import logging
import time
import random
from typing import List

import spidev
import gpiozero
from PIL import Image, ImageDraw, ImageFont

# ============================================================================
# RASPBERRY PI HARDWARE INTERFACE
# ============================================================================

logger = logging.getLogger(__name__)


class RaspberryPi:
    """
    Raspberry Pi GPIO and SPI interface handler for e-ink display.
    """
    # Pin definition
    RST_PIN: int = 17
    DC_PIN: int = 25
    CS_PIN: int = 8
    BUSY_PIN: int = 24
    PWR_PIN: int = 18
    MOSI_PIN: int = 10
    SCLK_PIN: int = 11

    def __init__(self) -> None:
        self.SPI = spidev.SpiDev()
        self.GPIO_RST_PIN = gpiozero.LED(self.RST_PIN)
        self.GPIO_DC_PIN = gpiozero.LED(self.DC_PIN)
        self.GPIO_PWR_PIN = gpiozero.LED(self.PWR_PIN)
        self.GPIO_BUSY_PIN = gpiozero.Button(self.BUSY_PIN, pull_up=False)

    def digital_write(self, pin: int, value: int) -> None:
        if pin == self.RST_PIN:
            if value:
                self.GPIO_RST_PIN.on()
            else:
                self.GPIO_RST_PIN.off()
        elif pin == self.DC_PIN:
            if value:
                self.GPIO_DC_PIN.on()
            else:
                self.GPIO_DC_PIN.off()
        elif pin == self.PWR_PIN:
            if value:
                self.GPIO_PWR_PIN.on()
            else:
                self.GPIO_PWR_PIN.off()

    def digital_read(self, pin: int) -> int:
        if pin == self.BUSY_PIN:
            return self.GPIO_BUSY_PIN.value
        elif pin == self.RST_PIN:
            return self.RST_PIN.value
        elif pin == self.DC_PIN:
            return self.DC_PIN.value
        elif pin == self.PWR_PIN:
            return self.PWR_PIN.value
        return 0

    def delay_ms(self, delaytime: float) -> None:
        time.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data: List[int]) -> None:
        self.SPI.writebytes(data)

    def module_init(self) -> int:
        self.GPIO_PWR_PIN.on()
        self.SPI.open(0, 0)
        self.SPI.max_speed_hz = 4000000
        self.SPI.mode = 0b00
        return 0

    def module_exit(self) -> None:
        logger.debug("spi end")
        try:
            self.SPI.close()
        except Exception as e:
            logger.debug(f"SPI close error: {e}")

        for pin, name in [(self.GPIO_RST_PIN, "RST"),
                          (self.GPIO_DC_PIN, "DC"),
                          (self.GPIO_PWR_PIN, "PWR"),
                          (self.GPIO_BUSY_PIN, "BUSY")]:
            try:
                pin.off() if hasattr(pin, 'off') else None
                pin.close()
            except Exception as e:
                logger.debug(f"{name} pin close error: {e}")

        logger.debug("Module enters 0 power consumption")


epdconfig = RaspberryPi()

# ============================================================================
# E-PAPER DISPLAY DRIVER
# ============================================================================

# Display resolution
EPD_WIDTH = 800
EPD_HEIGHT = 480

GRAY1 = 0xff  # white
GRAY2 = 0xC0
GRAY3 = 0x80  # gray
GRAY4 = 0x00  # Blackest


class EPD:
    def __init__(self):
        self.reset_pin = epdconfig.RST_PIN
        self.dc_pin = epdconfig.DC_PIN
        self.busy_pin = epdconfig.BUSY_PIN
        self.cs_pin = epdconfig.CS_PIN
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT
        self.GRAY1 = GRAY1
        self.GRAY2 = GRAY2
        self.GRAY3 = GRAY3
        self.GRAY4 = GRAY4

    def reset(self):
        epdconfig.digital_write(self.reset_pin, 1)
        epdconfig.delay_ms(20)
        epdconfig.digital_write(self.reset_pin, 0)
        epdconfig.delay_ms(2)
        epdconfig.digital_write(self.reset_pin, 1)
        epdconfig.delay_ms(20)

    def send_command(self, command):
        epdconfig.digital_write(self.dc_pin, 0)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte([command])
        epdconfig.digital_write(self.cs_pin, 1)

    def send_data(self, data):
        epdconfig.digital_write(self.dc_pin, 1)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte([data])
        epdconfig.digital_write(self.cs_pin, 1)

    def send_data2(self, data):
        epdconfig.digital_write(self.dc_pin, 1)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.SPI.writebytes2(data)
        epdconfig.digital_write(self.cs_pin, 1)

    def ReadBusy(self):
        logger.debug("e-Paper busy")
        self.send_command(0x71)
        busy = epdconfig.digital_read(self.busy_pin)
        while busy == 0:
            self.send_command(0x71)
            busy = epdconfig.digital_read(self.busy_pin)
        epdconfig.delay_ms(20)
        logger.debug("e-Paper busy release")

    def init(self):
        if epdconfig.module_init() != 0:
            return -1
        self.reset()

        self.send_command(0x06)  # btst
        self.send_data(0x17)
        self.send_data(0x17)
        self.send_data(0x28)
        self.send_data(0x17)

        self.send_command(0x01)  # POWER SETTING
        self.send_data(0x07)
        self.send_data(0x07)
        self.send_data(0x28)
        self.send_data(0x17)

        self.send_command(0x04)  # POWER ON
        epdconfig.delay_ms(100)
        self.ReadBusy()

        self.send_command(0X00)  # PANNEL SETTING
        self.send_data(0x1F)

        self.send_command(0x61)  # tres
        self.send_data(0x03)
        self.send_data(0x20)
        self.send_data(0x01)
        self.send_data(0xE0)

        self.send_command(0X15)
        self.send_data(0x00)

        self.send_command(0X50)
        self.send_data(0x10)
        self.send_data(0x07)

        self.send_command(0X60)  # TCON SETTING
        self.send_data(0x22)

        return 0

    def init_part(self):
        if epdconfig.module_init() != 0:
            return -1
        self.reset()

        self.send_command(0X00)  # PANNEL SETTING
        self.send_data(0x1F)

        self.send_command(0x04)  # POWER ON
        epdconfig.delay_ms(100)
        self.ReadBusy()

        self.send_command(0xE0)
        self.send_data(0x02)
        self.send_command(0xE5)
        self.send_data(0x6E)

        return 0

    def getbuffer(self, image):
        img = image
        imwidth, imheight = img.size
        if imwidth == self.width and imheight == self.height:
            img = img.convert('1')
        elif imwidth == self.height and imheight == self.width:
            img = img.rotate(90, expand=True).convert('1')
        else:
            logger.warning("Wrong image dimensions")
            return [0x00] * (int(self.width / 8) * self.height)

        buf = bytearray(img.tobytes('raw'))
        for i in range(len(buf)):
            buf[i] ^= 0xFF
        return buf

    def display(self, image):
        if self.width % 8 == 0:
            Width = self.width // 8
        else:
            Width = self.width // 8 + 1
        Height = self.height
        image1 = [0xFF] * int(self.width * self.height / 8)
        for j in range(Height):
            for i in range(Width):
                image1[i + j * Width] = ~image[i + j * Width]
        self.send_command(0x10)
        self.send_data2(image1)

        self.send_command(0x13)
        self.send_data2(image)

        self.send_command(0x12)
        epdconfig.delay_ms(100)
        self.ReadBusy()

    def Clear(self):
        self.send_command(0x10)
        self.send_data2([0xFF] * int(self.width * self.height / 8))
        self.send_command(0x13)
        self.send_data2([0x00] * int(self.width * self.height / 8))

        self.send_command(0x12)
        epdconfig.delay_ms(100)
        self.ReadBusy()

    def display_Partial(self, Image, Xstart, Ystart, Xend, Yend):
        if ((Xstart % 8 + Xend % 8 == 8 & Xstart % 8 > Xend % 8) |
                Xstart % 8 + Xend % 8 == 0 | (Xend - Xstart) % 8 == 0):
            Xstart = Xstart // 8 * 8
            Xend = Xend // 8 * 8
        else:
            Xstart = Xstart // 8 * 8
            if Xend % 8 == 0:
                Xend = Xend // 8 * 8
            else:
                Xend = Xend // 8 * 8 + 1

        Width = (Xend - Xstart) // 8
        Height = Yend - Ystart

        self.send_command(0x50)
        self.send_data(0xA9)
        self.send_data(0x07)

        self.send_command(0x91)
        self.send_command(0x90)
        self.send_data(Xstart // 256)
        self.send_data(Xstart % 256)
        self.send_data((Xend - 1) // 256)
        self.send_data((Xend - 1) % 256)
        self.send_data(Ystart // 256)
        self.send_data(Ystart % 256)
        self.send_data((Yend - 1) // 256)
        self.send_data((Yend - 1) % 256)
        self.send_data(0x01)

        image1 = [0xFF] * int(self.width * self.height / 8)
        for j in range(Height):
            for i in range(Width):
                image1[i + j * Width] = ~Image[i + j * Width]

        self.send_command(0x13)
        self.send_data2(image1)

        self.send_command(0x12)
        epdconfig.delay_ms(100)
        self.ReadBusy()

    def sleep(self):
        self.send_command(0x50)
        self.send_data(0XF7)

        self.send_command(0x02)  # POWER_OFF
        self.ReadBusy()

        self.send_command(0x07)  # DEEP_SLEEP
        self.send_data(0XA5)

        epdconfig.delay_ms(2000)
        epdconfig.module_exit()


# ============================================================================
# MATRIX ANIMATION
# ============================================================================

class MatrixColumn:
    def __init__(self, x, height, font, symbols):
        self.x = x
        self.height = height
        self.font = font
        self.symbols = symbols
        self.chars = []
        self.speed = random.randint(1, 3)
        self.length = random.randint(5, 15)
        self.y = random.randint(-height, 0)
        self.char_height = 24

    def update(self):
        self.y += self.speed
        if self.y > self.height:
            self.y = random.randint(-self.height // 2, 0)
            self.length = random.randint(5, 15)
            self.speed = random.randint(1, 3)

    def get_chars(self):
        chars = []
        for i in range(self.length):
            char_y = self.y - (i * self.char_height)
            if 0 <= char_y < self.height:
                chars.append((self.x, char_y, random.choice(self.symbols)))
        return chars


def main():
    logging.basicConfig(level=logging.INFO)

    try:
        logging.info("Matrix Animation - Initializing e-Paper")
        epd = EPD()

        # Initialize and clear
        logging.info("Clearing screen...")
        epd.init()
        epd.Clear()

        # Initialize for partial updates
        logging.info("Initializing partial refresh mode...")
        epd.init_part()

        # Load font with Japanese character support
        font = None
        font_paths = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansMonoCJKjp-Regular.otf",
            "/usr/share/fonts/truetype/takao-gothic/TakaoPGothic.ttf",
            "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",  # macOS
        ]

        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, 18)
                logging.info(f"Loaded font: {font_path}")
                break
            except:
                continue

        if font is None:
            logging.warning("No CJK font found. Install with: sudo apt-get install fonts-noto-cjk")
            font = ImageFont.load_default()

        # Unicode symbols for Matrix effect
        symbols = [
            # Katakana
            'ア', 'イ', 'ウ', 'エ', 'オ', 'カ', 'キ', 'ク', 'ケ', 'コ',
            'サ', 'シ', 'ス', 'セ', 'ソ', 'タ', 'チ', 'ツ', 'テ', 'ト',
            'ナ', 'ニ', 'ヌ', 'ネ', 'ノ', 'ハ', 'ヒ', 'フ', 'ヘ', 'ホ',
            # Numbers and symbols
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            ':', '・', '=', '*', '+', '-', '<', '>', '¦', '|',
            # Latin
            'Z', 'A', 'X', 'N', 'M', 'K', 'L', 'R', 'T', 'Y'
        ]

        # Create columns
        num_columns = epd.width // 20
        columns = []
        for i in range(num_columns):
            x = i * 20 + 5
            col = MatrixColumn(x, epd.height, font, symbols)
            columns.append(col)

        # Create base image
        image = Image.new('1', (epd.width, epd.height), 255)

        logging.info("Starting animation... (Press Ctrl+C to stop)")
        frame = 0

        while True:
            # Clear previous frame
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, epd.width, epd.height), fill=255)

            # Update and draw columns
            for col in columns:
                col.update()
                chars = col.get_chars()
                for x, y, char in chars:
                    try:
                        draw.text((x, y), char, font=font, fill=0)
                    except:
                        pass

            # Partial refresh (ghosting creates interesting layered aesthetic)
            epd.display_Partial(epd.getbuffer(image), 0, 0, epd.width, epd.height)

            frame += 1
            if frame % 50 == 0:
                logging.info(f"Frame {frame}")

            # Small delay to control animation speed
            time.sleep(0.1)

    except KeyboardInterrupt:
        logging.info("Animation stopped by user")
    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logging.info("Cleaning up...")
        try:
            epd.init()
            epd.Clear()
            epd.sleep()
        except:
            pass
        epdconfig.module_exit()


if __name__ == '__main__':
    main()