# *****************************************************************************
# * | File        :	  esl.py
# * | Author      :   Liam Cornu
# * | Credits     :   Waveshare Team
# * | Function    :   Custom Driver for GDisplay SES Imagotag screens
# * | Info        :
# *----------------
# * | This version:   V1.2 - Dynamic resolution support
# * | Date        :   2025-10-08
# *****************************************************************************

import time
import logging
from typing import List, Tuple, Optional
from PIL import Image
import spidev
import gpiozero

# Display resolution
EPD_WIDTH: int = 168
EPD_HEIGHT: int = 384

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class RaspberryPi:
    """
    Raspberry Pi GPIO and SPI interface handler for e-ink display.

    Manages hardware communication including GPIO pins for control signals
    and SPI bus for data transfer to the e-ink display controller.

    Attributes:
        RST_PIN (int): Reset pin GPIO number
        DC_PIN (int): Data/Command pin GPIO number
        CS_PIN (int): Chip Select pin GPIO number
        BUSY_PIN (int): Busy status pin GPIO number
        PWR_PIN (int): Power control pin GPIO number
        MOSI_PIN (int): SPI MOSI pin GPIO number
        SCLK_PIN (int): SPI clock pin GPIO number
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
        """
        Initialize Raspberry Pi GPIO and SPI interfaces.

        Sets up GPIO pins for display control and configures SPI device
        for communication with the e-ink display controller.
        """


        self.SPI = spidev.SpiDev()
        self.GPIO_RST_PIN = gpiozero.LED(self.RST_PIN)
        self.GPIO_DC_PIN = gpiozero.LED(self.DC_PIN)
        self.GPIO_PWR_PIN = gpiozero.LED(self.PWR_PIN)
        self.GPIO_BUSY_PIN = gpiozero.Button(self.BUSY_PIN, pull_up=False)

    def digital_write(self, pin: int, value: int) -> None:
        """
        Write a digital value to a GPIO pin.

        Args:
            pin: GPIO pin number to write to
            value: Digital value to write (0 for LOW, non-zero for HIGH)
        """
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

    def digital_read(self, pin):
        """
        Read a digital value from a GPIO pin.

        Args:
            pin: GPIO pin number to read from

        Returns:
            Digital value (0 for LOW, 1 for HIGH)
        """
        if pin == self.BUSY_PIN:
            return self.GPIO_BUSY_PIN.value
        elif pin == self.RST_PIN:
            return self.RST_PIN.value
        elif pin == self.DC_PIN:
            return self.DC_PIN.value
        elif pin == self.PWR_PIN:
            return self.PWR_PIN.value

    def delay_ms(self, delaytime: float) -> None:
        """
        Delay execution for specified milliseconds.

        Args:
            delaytime: Delay duration in milliseconds
        """
        time.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data: List[int]) -> None:
        """
        Write bytes to the SPI bus.

        Args:
            data: List of byte values to write
        """
        self.SPI.writebytes(data)

    def module_init(self) -> int:
        """
        Initialize the hardware module.

        Powers on the display and configures SPI communication parameters.

        Returns:
            0 on success, -1 on failure
        """
        self.GPIO_PWR_PIN.on()
        # SPI device, bus = 0, device = 0
        self.SPI.open(0, 0)
        self.SPI.max_speed_hz = 4000000
        self.SPI.mode = 0b00
        return 0

    def module_exit(self) -> None:
        """
        Safely shut down the hardware module.

        Closes SPI connection, turns off GPIO pins, and enters
        zero power consumption mode.
        """
        logger.debug("spi end")
        self.SPI.close()

        self.GPIO_RST_PIN.off()
        self.GPIO_DC_PIN.off()
        self.GPIO_PWR_PIN.off()
        logger.debug("close 5V, Module enters 0 power consumption ...")

        self.GPIO_RST_PIN.close()
        self.GPIO_DC_PIN.close()
        self.GPIO_PWR_PIN.close()
        self.GPIO_BUSY_PIN.close()


epdconfig: RaspberryPi = RaspberryPi()


def module_exit() -> None:
    """
    Exit the module and clean up hardware resources.

    Calls the underlying hardware module exit routine to safely
    shut down all GPIO and SPI connections.
    """
    epdconfig.module_exit()


class EPD:
    """
    E-Paper Display (EPD) driver for SES Imagotag ESL screens (GDisplay).

    Provides high-level interface for controlling e-ink displays with
    black/white and red/yellow color support. Handles display initialization,
    image rendering, and power management.

    Attributes:
        reset_pin (int): GPIO pin for hardware reset
        dc_pin (int): GPIO pin for data/command selection
        busy_pin (int): GPIO pin for busy status monitoring
        cs_pin (int): GPIO pin for chip select
        width (int): Display width in pixels
        height (int): Display height in pixels
    """

    def __init__(self) -> None:
        """
        Initialize the EPD driver with default display parameters.

        Sets up pin assignments and display dimensions from global constants.
        """
        self.reset_pin: int = epdconfig.RST_PIN
        self.dc_pin: int = epdconfig.DC_PIN
        self.busy_pin: int = epdconfig.BUSY_PIN
        self.cs_pin: int = epdconfig.CS_PIN
        self.width: int = EPD_WIDTH
        self.height: int = EPD_HEIGHT

    def reset(self) -> None:
        """
        Perform hardware reset of the e-ink display.

        Executes reset sequence by toggling the reset pin with appropriate
        timing delays to ensure proper display controller initialization.
        """
        epdconfig.digital_write(self.reset_pin, 1)
        epdconfig.delay_ms(200)
        epdconfig.digital_write(self.reset_pin, 0)
        epdconfig.delay_ms(5)
        epdconfig.digital_write(self.reset_pin, 1)
        epdconfig.delay_ms(200)

    def send_command(self, command: int) -> None:
        """
        Send a command byte to the display controller.

        Args:
            command: Command byte to send (0x00-0xFF)
        """
        epdconfig.digital_write(self.dc_pin, 0)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte([command])
        epdconfig.digital_write(self.cs_pin, 1)

    def send_data(self, data: int) -> None:
        """
        Send a data byte to the display controller.

        Args:
            data: Data byte to send (0x00-0xFF)
        """
        epdconfig.digital_write(self.dc_pin, 1)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte([data])
        epdconfig.digital_write(self.cs_pin, 1)

    def ReadBusy(self) -> None:
        """
        Wait for the display to complete current operation.

        Polls the busy pin until the display controller signals it's ready
        for the next command. Busy = 0 (idle), Busy = 1 (processing).
        """
        logger.debug("e-Paper busy")
        while epdconfig.digital_read(self.busy_pin) == 0:  # 0: idle, 1: busy
            epdconfig.delay_ms(200)
        logger.debug("e-Paper busy release")

    def init(self) -> int:
        """
        Initialize the e-ink display controller.

        Performs hardware initialization sequence including power boost,
        panel settings, and resolution configuration.

        Returns:
            0 on success, -1 on failure
        """
        if epdconfig.module_init() != 0:
            return -1
        # EPD hardware init start
        self.reset()

        self.send_command(0x06)  # boost
        self.send_data(0x17)
        self.send_data(0x17)
        self.send_data(0x17)
        self.send_command(0x04)  # POWER_ON
        self.ReadBusy()
        self.send_command(0X00)  # PANEL_SETTING
        self.send_data(0x8F)
        self.send_command(0X50)  # VCOM_AND_DATA_INTERVAL_SETTING
        self.send_data(0x77)

        # TCON_RESOLUTION
        self.send_command(0x61)

        # Calculate and send width (low byte, high byte if needed)
        width_low: int = self.width & 0xFF
        width_high: int = (self.width >> 8) & 0xFF

        # Calculate and send height
        height_low: int = self.height & 0xFF
        height_high: int = (self.height >> 8) & 0xFF

        # Send resolution data
        # Format typically: width_low, width_high, height_low, height_high
        # But some displays use: width, height_high, height_low

        # Standard format
        # self.send_data(width_low)
        # self.send_data(width_high)
        # self.send_data(height_low)
        # self.send_data(height_high)

        # Alternative format
        self.send_data(width_low)
        self.send_data(height_high)
        self.send_data(height_low)

        logger.debug(f"Setting resolution to {self.width}x{self.height}")
        logger.debug(f"Resolution bytes: {width_low:02x} {width_high:02x} {height_low:02x} {height_high:02x}")

        # VCOM DC Setting - Uncomment to adjust contrast/ghosting
        # Controls the common voltage for better image quality
        # self.send_command(VCM_DC_SETTING_REGISTER)
        # self.send_data(0x0A)

        return 0

    def getbuffer(self, image: Image.Image) -> List[int]:
        """
        Convert a PIL Image to display buffer format.

        Transforms an image into a byte array compatible with the e-ink display.
        Supports both vertical (matching display orientation) and horizontal
        (rotated) image inputs. Black pixels are set as 0 bits, white as 1 bits.

        Args:
            image: PIL Image object to convert

        Returns:
            List of bytes representing the image in display format
        """
        logger.debug("bufsiz = ", int(self.width / 8) * self.height)
        buf: List[int] = [0xFF] * (int(self.width / 8) * self.height)
        image_monocolor: Image.Image = image.convert('1')
        imwidth: int
        imheight: int
        imwidth, imheight = image_monocolor.size
        pixels = image_monocolor.load()
        logger.debug("imwidth = %d, imheight = %d", imwidth, imheight)
        if imwidth == self.width and imheight == self.height:
            logger.debug("Vertical")
            for y in range(imheight):
                for x in range(imwidth):
                    # Set the bits for the column of pixels at the current position.
                    if pixels[x, y] == 0:
                        buf[int((x + y * self.width) / 8)] &= ~(0x80 >> (x % 8))
        elif imwidth == self.height and imheight == self.width:
            logger.debug("Horizontal")
            for y in range(imheight):
                for x in range(imwidth):
                    newx: int = y
                    newy: int = self.height - x - 1
                    if pixels[x, y] == 0:
                        buf[int((newx + newy * self.width) / 8)] &= ~(0x80 >> (y % 8))
        return buf

    def display(self, blackimage: Optional[List[int]], ryimage: Optional[List[int]]) -> None:
        """
        Update the e-ink display with new image data.

        Sends black/white image data and red/yellow image data to the display
        controller and triggers a screen refresh.

        Args:
            blackimage: Buffer containing black/white pixel data (None to skip)
            ryimage: Buffer containing red/yellow pixel data (None to skip)
        """
        if blackimage is not None:
            self.send_command(0X10)
            for i in range(0, int(self.width * self.height / 8)):
                self.send_data(blackimage[i])
        if ryimage is not None:
            self.send_command(0X13)
            for i in range(0, int(self.width * self.height / 8)):
                self.send_data(ryimage[i])

        self.send_command(0x12)
        self.ReadBusy()

    def separate_colors(self, image_path: str, use_dithering: bool = True) -> Tuple[Image.Image, Image.Image]:
        """
        Separates colors using indexed palette

        Handles transparency different color modes and converts them for the e-ink display.

        Args:
            image_path: Path to the source image file (PNG, JPEG, WebP, BMP, etc.)
            use_dithering: Whether to apply Floyd-Steinberg dithering for better gradients

        Returns:
            Tuple of (HBlackimage, HRYimage) ready for display
        """
        # Load the original image
        original: Image.Image = Image.open(image_path)

        # Handle different image modes
        if original.mode in ('RGBA', 'LA', 'PA'):
            # Images with alpha channel - composite onto white background
            background = Image.new('RGB', original.size, (255, 255, 255))
            if original.mode == 'P':
                # Convert palette mode to RGBA first
                original = original.convert('RGBA')
            background.paste(original, mask=original.split()[-1])  # Use alpha as mask
            original = background
        elif original.mode != 'RGB':
            # Any other mode - force to RGB
            original = original.convert('RGB')

        width, height = original.size

        # Validate dimensions
        if width != self.width or height != self.height:
            logger.warning(f"Image dimensions {width}x{height} don't match display {self.width}x{self.height}")
            logger.info("Resizing image to fit display...")
            original = original.resize((self.width, self.height), Image.Resampling.LANCZOS)
            width, height = self.width, self.height

        # Create 3-color palette
        pal_image = Image.new("P", (1, 1))
        pal_image.putpalette(
            (0, 0, 0,  # Index 0: Black
             255, 255, 255,  # Index 1: White
             255, 0, 0)  # Index 2: Red
            + (0, 0, 0) * 253  # Pad to 256 colors
        )

        # Quantize to palette with optional dithering
        dither_mode = Image.Dither.FLOYDSTEINBERG if use_dithering else Image.Dither.NONE
        quantized = original.quantize(palette=pal_image, dither=dither_mode)

        # Work directly with palette indices (0, 1, or 2)
        pixel_data = list(quantized.getdata())

        # Create output images in mode '1' (pure black/white bitmap)
        hblackimage = Image.new('1', (width, height), 1)  # Start white (1)
        hryimage = Image.new('1', (width, height), 1)

        black_pixels = hblackimage.load()
        ry_pixels = hryimage.load()

        # Process by index - fast and efficient
        for i, color_index in enumerate(pixel_data):
            x = i % width
            y = i // width

            if color_index == 0:  # Black
                black_pixels[x, y] = 0
            elif color_index == 2:  # Red/Yellow
                ry_pixels[x, y] = 0
            # Index 1 (white) - already set to 1

        return hblackimage, hryimage

    def Clear(self) -> None:
        """
        Clear the entire display to white.

        Sends all-white data to both black and red/yellow buffers,
        then triggers a refresh to clear the screen.
        """
        self.send_command(0X10)
        for i in range(0, int(self.width * self.height / 8)):
            self.send_data(0xff)
        self.send_command(0X13)
        for i in range(0, int(self.width * self.height / 8)):
            self.send_data(0xff)

        self.send_command(0x12)
        self.ReadBusy()

    def sleep(self) -> None:
        """
        Put the display into deep sleep mode.

        Powers down the display controller and exits to zero power consumption.
        Display must be reinitialized with init() before next use.
        """
        self.send_command(0X02)  # power off
        self.ReadBusy()
        self.send_command(0X07)  # deep sleep
        self.send_data(0xA5)

        epdconfig.delay_ms(2000)
        epdconfig.module_exit()