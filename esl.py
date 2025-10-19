# *****************************************************************************
# * | File        :	  esl.py
# * | Author      :   Liam Cornu
# * | Credits     :   Waveshare Team
# * | Function    :   Custom Driver for 2.9" GDisplay SES Imagotag screens
# * | Info        :
# *----------------
# * | This version:   V2.0 - Cleaned for ESL display limitations
# * | Date        :   2025-10-19
# *****************************************************************************

import time
import logging
from typing import List, Tuple, Optional
from PIL import Image
import spidev
import gpiozero

# Display resolution (portrait orientation)
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

    def digital_read(self, pin: int) -> int:
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
        return 0

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
        self.SPI.open(0, 0)
        self.SPI.max_speed_hz = 4000000
        self.SPI.mode = 0b00
        return 0

    def module_exit(self) -> None:
        """
        Safely shut down the hardware module.

        Closes SPI connection, turns off GPIO pins, and enters
        zero power consumption mode. Handles already-closed pins gracefully.
        """
        logger.debug("spi end")

        try:
            self.SPI.close()
        except Exception as e:
            logger.debug(f"SPI close error (may already be closed): {e}")

        # Safely turn off pins even if already closed
        try:
            self.GPIO_RST_PIN.off()
        except Exception as e:
            logger.debug(f"RST pin close error (may already be closed): {e}")

        try:
            self.GPIO_DC_PIN.off()
        except Exception as e:
            logger.debug(f"DC pin close error (may already be closed): {e}")

        try:
            self.GPIO_PWR_PIN.off()
        except Exception as e:
            logger.debug(f"PWR pin close error (may already be closed): {e}")

        logger.debug("close 5V, Module enters 0 power consumption ...")

        # Close GPIO pin objects
        try:
            self.GPIO_RST_PIN.close()
        except Exception as e:
            logger.debug(f"RST pin object close error: {e}")

        try:
            self.GPIO_DC_PIN.close()
        except Exception as e:
            logger.debug(f"DC pin object close error: {e}")

        try:
            self.GPIO_PWR_PIN.close()
        except Exception as e:
            logger.debug(f"PWR pin object close error: {e}")

        try:
            self.GPIO_BUSY_PIN.close()
        except Exception as e:
            logger.debug(f"BUSY pin object close error: {e}")


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

    Provides interface for controlling e-ink displays with black/white
    and red/yellow color support.

    DISPLAY CAPABILITIES:
    ✓ Full screen refresh (168x384, ~21 seconds)
    ✓ Partial area refresh from (0,0) - preserves static content below
    ✓ Black/white and red/yellow color support
    ✓ Portrait (168x384) and landscape (384x168) image handling

    DISPLAY LIMITATIONS:
    ✗ No speed benefit from partial refresh (~21s for any size)
    ✗ Partial refresh always starts from (0,0) - position cannot be changed
    ✗ Red/yellow layer not supported in partial mode
    ✗ No fast refresh modes

    BEST USE CASES:
    - Infrequent updates (minutes/hours between changes)
    - Static information displays (prices, schedules, status boards)
    - Designs with dynamic top section + static bottom section

    Attributes:
        reset_pin (int): GPIO pin for hardware reset
        dc_pin (int): GPIO pin for data/command selection
        busy_pin (int): GPIO pin for busy status monitoring
        cs_pin (int): GPIO pin for chip select
        width (int): Display width in pixels (168)
        height (int): Display height in pixels (384)
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
        Initialize the e-ink display controller for full screen mode.

        Performs hardware initialization sequence including power boost,
        panel settings, and resolution configuration.

        Returns:
            0 on success, -1 on failure
        """
        if epdconfig.module_init() != 0:
            return -1

        self.reset()

        self.send_command(0x06)  # Boost
        self.send_data(0x17)
        self.send_data(0x17)
        self.send_data(0x17)

        self.send_command(0x04)  # Power on
        self.ReadBusy()

        self.send_command(0x00)  # Panel setting
        self.send_data(0x8F)

        self.send_command(0x50)  # VCOM and data interval setting
        self.send_data(0x77)

        # Set resolution
        self.send_command(0x61)  # TCON resolution
        self.send_data(self.width & 0xFF)
        self.send_data((self.height >> 8) & 0xFF)
        self.send_data(self.height & 0xFF)

        logger.debug(f"Display initialized: {self.width}x{self.height}")

        return 0

    def init_partial(self, height: int) -> int:
        """
        Initialize display for partial area refresh from top-left (0,0).

        IMPORTANT LIMITATIONS:
        - Always updates from position (0,0) - cannot change position
        - Takes same time as full refresh (~21s) - no speed benefit
        - Only benefit: preserves static content below the partial area

        Use case: Display with dynamic top portion and static bottom portion.
        Example: Clock at top (updates frequently) with labels at bottom (static)

        Args:
            height: Height of the partial area to update (0 to 384)

        Returns:
            0 on success, -1 on failure
        """
        # Set resolution to partial area size
        # This controls which pixels get refreshed
        self.send_command(0x61)  # TCON resolution
        self.send_data(self.width & 0xFF)
        self.send_data((height >> 8) & 0xFF)
        self.send_data(height & 0xFF)

        logger.debug(f"Partial area configured: {self.width}x{height} from (0,0)")
        logger.debug("Note: Refresh takes ~21s (same as full screen)")

        return 0

    def getbuffer(self, image: Image.Image) -> List[int]:
        """
        Convert a PIL Image to display buffer format.

        Transforms an image into a byte array compatible with the e-ink display.
        Supports both portrait (168x384) and landscape (384x168) orientations.
        Black pixels are set as 0 bits, white as 1 bits.

        Args:
            image: PIL Image object to convert

        Returns:
            List of bytes representing the image in display format
        """
        buf: List[int] = [0xFF] * (int(self.width / 8) * self.height)
        image_monocolor: Image.Image = image.convert('1')
        imwidth, imheight = image_monocolor.size
        pixels = image_monocolor.load()

        logger.debug(f"Converting image: {imwidth}x{imheight}")

        if imwidth == self.width and imheight == self.height:
            # Portrait orientation (matches display native)
            logger.debug("Portrait orientation")
            for y in range(imheight):
                for x in range(imwidth):
                    if pixels[x, y] == 0:
                        buf[int((x + y * self.width) / 8)] &= ~(0x80 >> (x % 8))
        elif imwidth == self.height and imheight == self.width:
            # Landscape orientation (rotated 90°)
            logger.debug("Landscape orientation")
            for y in range(imheight):
                for x in range(imwidth):
                    newx: int = y
                    newy: int = self.height - x - 1
                    if pixels[x, y] == 0:
                        buf[int((newx + newy * self.width) / 8)] &= ~(0x80 >> (y % 8))
        else:
            logger.warning(f"Image size {imwidth}x{imheight} doesn't match display")

        return buf

    def display(self, blackimage: Optional[List[int]], ryimage: Optional[List[int]]) -> None:
        """
        Update the e-ink display with new image data.

        Sends black/white image data and red/yellow image data to the display
        controller and triggers a screen refresh. Takes approximately 21 seconds.

        Args:
            blackimage: Buffer containing black/white pixel data (None to skip)
            ryimage: Buffer containing red/yellow pixel data (None to skip)
        """
        if blackimage is not None:
            self.send_command(0x10)  # Write BW RAM
            for i in range(0, int(self.width * self.height / 8)):
                self.send_data(blackimage[i])

        if ryimage is not None:
            self.send_command(0x13)  # Write RED RAM
            for i in range(0, int(self.width * self.height / 8)):
                self.send_data(ryimage[i])

        self.send_command(0x12)  # Display refresh
        self.ReadBusy()

    def display_partial(self, blackimage: List[int], height: int) -> None:
        """
        Update only a partial area of the display from top-left (0,0).

        IMPORTANT: Call init_partial(height) first to configure the area.

        LIMITATIONS:
        - Always starts from position (0,0) - cannot be moved
        - Takes ~21 seconds (same as full screen) - no speed benefit
        - Red/yellow layer not supported for partial updates

        BENEFIT:
        - Static content below the partial area is preserved without refresh
        - Reduces ghosting accumulation on static elements

        Args:
            blackimage: Buffer for the partial area (must match configured height)
            height: Height of the partial area (must match init_partial call)
        """
        buffer_size = int(self.width * height / 8)

        if len(blackimage) != buffer_size:
            logger.warning(f"Buffer size mismatch: {len(blackimage)} != {buffer_size}")

        # Write black/white data for partial area
        self.send_command(0x10)
        for i in range(min(len(blackimage), buffer_size)):
            self.send_data(blackimage[i])

        # Clear red/yellow layer for partial area
        self.send_command(0x13)
        for i in range(buffer_size):
            self.send_data(0xFF)

        # Trigger refresh (will only update the configured partial area)
        self.send_command(0x12)
        self.ReadBusy()

    def getbuffer_partial(self, image: Image.Image, height: int) -> List[int]:
        """
        Convert a partial image to display buffer format.

        The image should be sized for the partial area (168 x height).

        Args:
            image: PIL Image in portrait orientation (168 x height)
            height: Height of the partial area

        Returns:
            Buffer for the partial area
        """
        buf: List[int] = [0xFF] * (int(self.width * height / 8))
        image_mono = image.convert('1')
        imwidth, imheight = image_mono.size
        pixels = image_mono.load()

        if imwidth != self.width or imheight != height:
            logger.warning(f"Partial image size {imwidth}x{imheight} doesn't match {self.width}x{height}")
            return buf

        logger.debug(f"Converting partial image: {imwidth}x{imheight}")

        for y in range(imheight):
            for x in range(imwidth):
                if pixels[x, y] == 0:
                    buf[int((x + y * self.width) / 8)] &= ~(0x80 >> (x % 8))

        return buf

    def separate_colors(self, image_path: str, use_dithering: bool = True) -> Tuple[Image.Image, Image.Image]:
        """
        Separate an image into black/white and red/yellow layers.

        Handles transparency, different color modes, and converts them for
        the e-ink display's three-color palette.

        Args:
            image_path: Path to the source image file
            use_dithering: Whether to apply Floyd-Steinberg dithering

        Returns:
            Tuple of (black_image, red_yellow_image) ready for display
        """
        # Load and convert image
        original: Image.Image = Image.open(image_path)

        # Handle transparency
        if original.mode in ('RGBA', 'LA', 'PA'):
            background = Image.new('RGB', original.size, (255, 255, 255))
            if original.mode == 'P':
                original = original.convert('RGBA')
            background.paste(original, mask=original.split()[-1])
            original = background
        elif original.mode != 'RGB':
            original = original.convert('RGB')

        width, height = original.size

        # Resize if needed
        if width != self.width or height != self.height:
            logger.warning(f"Resizing {width}x{height} to {self.width}x{self.height}")
            original = original.resize((self.width, self.height), Image.Resampling.LANCZOS)
            width, height = self.width, self.height

        # Create 3-color palette (black, white, red)
        pal_image = Image.new("P", (1, 1))
        pal_image.putpalette(
            (0, 0, 0,  # Index 0: Black
             255, 255, 255,  # Index 1: White
             255, 0, 0)  # Index 2: Red
            + (0, 0, 0) * 253  # Pad to 256 colors
        )

        # Quantize to palette
        dither_mode = Image.Dither.FLOYDSTEINBERG if use_dithering else Image.Dither.NONE
        quantized = original.quantize(palette=pal_image, dither=dither_mode)
        pixel_data = list(quantized.getdata())

        # Create output layers
        black_image = Image.new('1', (width, height), 1)
        red_image = Image.new('1', (width, height), 1)
        black_pixels = black_image.load()
        red_pixels = red_image.load()

        # Separate colors
        for i, color_index in enumerate(pixel_data):
            x = i % width
            y = i // width
            if color_index == 0:  # Black
                black_pixels[x, y] = 0
            elif color_index == 2:  # Red/Yellow
                red_pixels[x, y] = 0

        return black_image, red_image

    def Clear(self) -> None:
        """
        Clear the entire display to white.

        Sends all-white data to both black and red/yellow buffers,
        then triggers a refresh to clear the screen.
        """
        self.send_command(0x10)
        for i in range(0, int(self.width * self.height / 8)):
            self.send_data(0xFF)

        self.send_command(0x13)
        for i in range(0, int(self.width * self.height / 8)):
            self.send_data(0xFF)

        self.send_command(0x12)
        self.ReadBusy()

    def sleep(self) -> None:
        """
        Put the display into deep sleep mode.

        Powers down the display controller for zero power consumption.
        Display must be reinitialized with init() before next use.
        """
        self.send_command(0x02)  # Power off
        self.ReadBusy()
        self.send_command(0x07)  # Deep sleep
        self.send_data(0xA5)

        epdconfig.delay_ms(2000)
        epdconfig.module_exit()