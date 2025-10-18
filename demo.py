#!/usr/bin/python
# -*- coding:utf-8 -*-

import logging
import esl
import time
from PIL import ImageFont

logging.basicConfig(level=logging.DEBUG)

try:
    logging.info("epd2in9bc Demo")

    epd = esl.EPD()
    logging.info("init and Clear")
    epd.init()
    epd.Clear()

    # Drawing on the image
    logging.info("1.Drawing on the image...")

    hblackimage, hryimage = epd.separate_colors('image.bmp', False)
    epd.display(epd.getbuffer(hblackimage), epd.getbuffer(hryimage))
    time.sleep(2)

    logging.info("Goto Sleep...")
    epd.sleep()

except IOError as e:
    logging.info(e)

except KeyboardInterrupt:
    logging.info("ctrl + c:")
    esl.module_exit()
    exit()
