#!/usr/bin/python
# -*- coding:utf-8 -*-
"""
Animated Chinese Poetry with Art - Fully Animated, Minimal Whitespace
"""

import logging
import time
import random
import requests
import io
from typing import List, Optional, Dict

import spidev
import gpiozero
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# ============================================================================
# RASPBERRY PI HARDWARE INTERFACE
# ============================================================================

logger = logging.getLogger(__name__)


class RaspberryPi:
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
            self.GPIO_RST_PIN.on() if value else self.GPIO_RST_PIN.off()
        elif pin == self.DC_PIN:
            self.GPIO_DC_PIN.on() if value else self.GPIO_DC_PIN.off()
        elif pin == self.PWR_PIN:
            self.GPIO_PWR_PIN.on() if value else self.GPIO_PWR_PIN.off()

    def digital_read(self, pin: int) -> int:
        if pin == self.BUSY_PIN:
            return self.GPIO_BUSY_PIN.value
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
        try:
            self.SPI.close()
        except:
            pass
        for pin in [self.GPIO_RST_PIN, self.GPIO_DC_PIN, self.GPIO_PWR_PIN, self.GPIO_BUSY_PIN]:
            try:
                if hasattr(pin, 'off'):
                    pin.off()
                pin.close()
            except:
                pass


epdconfig = RaspberryPi()

# ============================================================================
# E-PAPER DISPLAY DRIVER
# ============================================================================

EPD_WIDTH = 800
EPD_HEIGHT = 480


class EPD:
    def __init__(self):
        self.reset_pin = epdconfig.RST_PIN
        self.dc_pin = epdconfig.DC_PIN
        self.busy_pin = epdconfig.BUSY_PIN
        self.cs_pin = epdconfig.CS_PIN
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT

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
        self.send_command(0x71)
        busy = epdconfig.digital_read(self.busy_pin)
        while busy == 0:
            self.send_command(0x71)
            busy = epdconfig.digital_read(self.busy_pin)
        epdconfig.delay_ms(20)

    def init(self):
        if epdconfig.module_init() != 0:
            return -1
        self.reset()
        self.send_command(0x06)
        self.send_data(0x17)
        self.send_data(0x17)
        self.send_data(0x28)
        self.send_data(0x17)
        self.send_command(0x01)
        self.send_data(0x07)
        self.send_data(0x07)
        self.send_data(0x28)
        self.send_data(0x17)
        self.send_command(0x04)
        epdconfig.delay_ms(100)
        self.ReadBusy()
        self.send_command(0X00)
        self.send_data(0x1F)
        self.send_command(0x61)
        self.send_data(0x03)
        self.send_data(0x20)
        self.send_data(0x01)
        self.send_data(0xE0)
        self.send_command(0X15)
        self.send_data(0x00)
        self.send_command(0X50)
        self.send_data(0x10)
        self.send_data(0x07)
        self.send_command(0X60)
        self.send_data(0x22)
        return 0

    def init_part(self):
        if epdconfig.module_init() != 0:
            return -1
        self.reset()
        self.send_command(0X00)
        self.send_data(0x1F)
        self.send_command(0x04)
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
            return [0x00] * (int(self.width / 8) * self.height)
        buf = bytearray(img.tobytes('raw'))
        for i in range(len(buf)):
            buf[i] ^= 0xFF
        return buf

    def display_Partial(self, Image, Xstart, Ystart, Xend, Yend):
        if ((Xstart % 8 + Xend % 8 == 8 & Xstart % 8 > Xend % 8) |
                Xstart % 8 + Xend % 8 == 0 | (Xend - Xstart) % 8 == 0):
            Xstart = Xstart // 8 * 8
            Xend = Xend // 8 * 8
        else:
            Xstart = Xstart // 8 * 8
            Xend = Xend // 8 * 8 if Xend % 8 == 0 else Xend // 8 * 8 + 1
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

    def Clear(self):
        self.send_command(0x10)
        self.send_data2([0xFF] * int(self.width * self.height / 8))
        self.send_command(0x13)
        self.send_data2([0x00] * int(self.width * self.height / 8))
        self.send_command(0x12)
        epdconfig.delay_ms(100)
        self.ReadBusy()

    def sleep(self):
        self.send_command(0x50)
        self.send_data(0XF7)
        self.send_command(0x02)
        self.ReadBusy()
        self.send_command(0x07)
        self.send_data(0XA5)
        epdconfig.delay_ms(2000)
        epdconfig.module_exit()


# ============================================================================
# CONTENT FETCHERS
# ============================================================================

class ContentFetcher:
    def __init__(self):
        self.fallback_poems = [
            {'content': '春眠不觉晓处处闻啼鸟夜来风雨声花落知多少', 'title': 'Spring Morning', 'author': '孟浩然'},
            {'content': '床前明月光疑是地上霜举头望明月低头思故乡', 'title': 'Quiet Night Thought', 'author': '李白'},
            {'content': '千山鸟飞绝万径人踪灭孤舟蓑笠翁独钓寒江雪', 'title': 'River Snow', 'author': '柳宗元'},
            {'content': '空山不见人但闻人语响返景入深林复照青苔上', 'title': 'Deer Park', 'author': '王维'},
            {'content': '红豆生南国春来发几枝愿君多采撷此物最相思', 'title': 'Lovesickness', 'author': '王维'},
            {'content': '白日依山尽黄河入海流欲穷千里目更上一层楼', 'title': 'Climbing Stork Tower',
             'author': '王之涣'},
            {'content': '独坐幽篁里弹琴复长啸深林人不知明月来相照', 'title': 'Bamboo Lodge', 'author': '王维'},
            {'content': '松下问童子言师采药去只在此山中云深不知处', 'title': 'Seeking the Recluse', 'author': '贾岛'},
        ]

    def fetch_poem(self) -> Dict:
        try:
            response = requests.get('https://v2.jinrishici.com/sentence', timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    content_data = data.get('data', {})
                    origin = content_data.get('origin', {})
                    content = content_data.get('content', '').replace('，', '').replace('。', '').replace('、',
                                                                                                        '').replace('；',
                                                                                                                    '').replace(
                        '：', '').replace('！', '').replace('？', '')
                    return {
                        'content': content,
                        'title': origin.get('title', 'Classical Poetry'),
                        'author': origin.get('author', 'Anonymous')
                    }
        except:
            pass
        return random.choice(self.fallback_poems)

    def fetch_art_image(self) -> Optional[Image.Image]:
        queries = ["chinese+ink+art", "oriental+painting", "asian+ink+painting", "sumi-e", "chinese+landscape"]
        try:
            query = random.choice(queries)
            # Try multiple image sources
            urls = [
                f"https://source.unsplash.com/500x480/?{query}",
                f"https://picsum.photos/500/480",
            ]

            for url in urls:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        return Image.open(io.BytesIO(response.content))
                except:
                    continue
        except:
            pass

        # Create a placeholder gradient image
        img = Image.new('L', (500, 480))
        for y in range(480):
            for x in range(500):
                img.putpixel((x, y), (x + y) % 256)
        return img


# ============================================================================
# ANIMATED DISPLAY WITH CASCADING TEXT
# ============================================================================

class CascadingPoetryDisplay:
    def __init__(self, width, height, font_zh, font_en):
        self.width = width
        self.height = height
        self.font_zh = font_zh
        self.font_en = font_en

        # Layout: 65% image on left, 35% text on right
        self.img_width = int(width * 0.65)
        self.text_x = self.img_width + 5
        self.text_width = width - self.text_x - 5

        # Current content
        self.current_image = None
        self.poem_queue = []
        self.char_grid = []  # 2D grid of characters with positions
        self.scroll_offset = 0

    def load_content(self, poem: Dict, image: Optional[Image.Image]):
        self.current_image = image
        self.poem_queue.append(poem)
        if len(self.poem_queue) > 3:
            self.poem_queue.pop(0)
        self._build_char_grid()
        logger.info(f"Loaded: {poem['title']} by {poem['author']}")

    def _build_char_grid(self):
        """Build dense grid of characters filling the text area"""
        self.char_grid = []
        char_size = 24
        spacing = 2

        # Calculate how many columns fit
        cols = (self.text_width - 10) // (char_size + spacing)
        y = 10

        # Fill with poems cyclically
        all_chars = []
        for poem in self.poem_queue:
            all_chars.extend(list(poem['content']))
            all_chars.append(' ')  # Small separator

        # Fill the entire height multiple times for scrolling
        total_chars_needed = cols * ((self.height * 3) // (char_size + spacing))
        while len(all_chars) < total_chars_needed:
            for poem in self.poem_queue:
                all_chars.extend(list(poem['content']))
                all_chars.append(' ')

        idx = 0
        while y < self.height * 3:
            for col in range(cols):
                x = self.text_x + 5 + col * (char_size + spacing)
                if idx < len(all_chars):
                    self.char_grid.append({
                        'char': all_chars[idx],
                        'x': x,
                        'y': y,
                        'col': col
                    })
                    idx += 1
            y += char_size + spacing

    def render_frame(self) -> Image.Image:
        canvas = Image.new('1', (self.width, self.height), 255)
        draw = ImageDraw.Draw(canvas)

        # Draw image on left
        if self.current_image:
            try:
                img = self.current_image.copy()
                img = img.resize((self.img_width - 10, self.height - 10), Image.Resampling.LANCZOS)
                img = img.convert('L')
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(2.5)
                img = img.convert('1')
                canvas.paste(img, (5, 5))
            except Exception as e:
                logger.warning(f"Image error: {e}")

        # Draw separator
        draw.line([(self.img_width, 0), (self.img_width, self.height)], fill=0, width=3)

        # Draw title at top
        if self.poem_queue:
            poem = self.poem_queue[-1]
            title_y = 8
            draw.text((self.text_x + 8, title_y), poem['title'], font=self.font_en, fill=0)
            draw.text((self.text_x + 8, title_y + 22), poem['author'], font=self.font_en, fill=0)
            # Underline
            draw.line([(self.text_x + 5, 52), (self.width - 5, 52)], fill=0, width=1)

        # Draw cascading characters
        for char_data in self.char_grid:
            y_pos = char_data['y'] - self.scroll_offset + 60
            if -30 <= y_pos <= self.height:
                # Add wave effect based on column
                wave_offset = int(5 * (1 + (char_data['col'] % 3)))
                final_y = y_pos + wave_offset
                if char_data['char'] != ' ':
                    draw.text((char_data['x'], final_y), char_data['char'], font=self.font_zh, fill=0)

        return canvas

    def update(self) -> bool:
        """Update animation - returns True if need new content"""
        self.scroll_offset += 2

        # Reset scroll and signal for new content
        if self.scroll_offset > self.height * 1.5:
            self.scroll_offset = 0
            return True
        return False


# ============================================================================
# MAIN
# ============================================================================

def main():
    logging.basicConfig(level=logging.INFO)

    try:
        logging.info("Starting Animated Chinese Poetry Display")
        epd = EPD()
        epd.init()
        epd.Clear()
        epd.init_part()

        # Load fonts
        font_zh = None
        font_en = None

        for path in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                     "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"]:
            try:
                font_zh = ImageFont.truetype(path, 22)
                break
            except:
                continue

        for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
            try:
                font_en = ImageFont.truetype(path, 16)
                break
            except:
                continue

        if not font_zh:
            font_zh = ImageFont.load_default()
            font_en = font_zh
        if not font_en:
            font_en = font_zh

        fetcher = ContentFetcher()
        display = CascadingPoetryDisplay(epd.width, epd.height, font_zh, font_en)

        # Pre-load content
        logging.info("Fetching initial content...")
        for _ in range(3):
            poem = fetcher.fetch_poem()
            display.poem_queue.append(poem)

        image = fetcher.fetch_art_image()
        display.current_image = image
        display._build_char_grid()

        logging.info("Animation started!")
        frame = 0

        while True:
            canvas = display.render_frame()
            epd.display_Partial(epd.getbuffer(canvas), 0, 0, epd.width, epd.height)

            needs_new = display.update()

            if needs_new:
                logging.info("Loading new content...")
                poem = fetcher.fetch_poem()
                image = fetcher.fetch_art_image()
                display.load_content(poem, image)

            frame += 1
            if frame % 30 == 0:
                logging.info(f"Frame {frame}")

            time.sleep(0.1)

    except KeyboardInterrupt:
        logging.info("Stopped")
    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            epd.Clear()
            epd.sleep()
        except:
            pass
        epdconfig.module_exit()


if __name__ == '__main__':
    main()