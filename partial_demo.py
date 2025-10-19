#!/usr/bin/python
# -*- coding:utf-8 -*-
"""
Practical demonstration of partial area updates.

Strategy:
- Full screen: Static labels and layout (bottom portion)
- Partial area: Dynamic content that updates (top portion)
- Result: Static content stays crisp, no ghosting accumulation
"""

import logging
import esl
import time
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

logging.basicConfig(level=logging.INFO)

try:
    logging.info("=" * 60)
    logging.info("ESL Partial Update Demo")
    logging.info("=" * 60)

    epd = esl.EPD()

    # Load fonts
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # =========================================================================
    # CONFIGURATION
    # =========================================================================
    # Define the partial update area (top portion, portrait orientation)
    PARTIAL_HEIGHT = 200  # Top 200 pixels will be dynamic
    STATIC_START = PARTIAL_HEIGHT  # Everything below is static

    logging.info(f"\nConfiguration:")
    logging.info(f"- Dynamic area: Top {PARTIAL_HEIGHT}px (0 to {PARTIAL_HEIGHT})")
    logging.info(f"- Static area: Bottom {384 - PARTIAL_HEIGHT}px ({STATIC_START} to 384)")

    # =========================================================================
    # STEP 1: Full screen initialization with static content
    # =========================================================================
    logging.info("\n[STEP 1] Full screen display with layout...")

    epd.init()
    epd.Clear()

    # Create full portrait image (168x384)
    full_image = Image.new('1', (168, 384), 255)
    draw = ImageDraw.Draw(full_image)

    # Draw separator line
    draw.line((0, PARTIAL_HEIGHT, 168, PARTIAL_HEIGHT), fill=0, width=3)

    # Draw static content (bottom portion) - THIS WON'T CHANGE
    draw.text((10, STATIC_START + 20), "Status Board", font=font_medium, fill=0)
    draw.text((10, STATIC_START + 50), "Location: Office 2B", font=font_small, fill=0)
    draw.text((10, STATIC_START + 70), "ESL Display v2.0", font=font_small, fill=0)
    draw.text((10, STATIC_START + 100), "Partial Updates:", font=font_small, fill=0)
    draw.text((10, STATIC_START + 120), "Top area only", font=font_small, fill=0)

    # Draw initial dynamic content (top portion)
    now = datetime.now()
    draw.text((10, 20), now.strftime('%H:%M'), font=font_large, fill=0)
    draw.text((10, 80), now.strftime('%A'), font=font_medium, fill=0)
    draw.text((10, 110), now.strftime('%B %d'), font=font_medium, fill=0)
    draw.text((10, 150), "Updates: 0", font=font_small, fill=0)

    # Display full screen
    epd.display(epd.getbuffer(full_image), None)
    logging.info("✓ Full screen displayed")
    logging.info("  Static content (bottom) will not be refreshed again")
    time.sleep(3)

    # =========================================================================
    # STEP 2: Configure for partial updates
    # =========================================================================
    logging.info(f"\n[STEP 2] Configuring partial area ({PARTIAL_HEIGHT}px)...")
    epd.init_partial(PARTIAL_HEIGHT)
    logging.info("✓ Partial mode configured")

    # =========================================================================
    # STEP 3: Update only the top portion repeatedly
    # =========================================================================
    logging.info("\n[STEP 3] Starting partial updates...")
    logging.info("Watch: Top area updates, bottom stays static")
    logging.info("Press Ctrl+C to stop\n")

    update_count = 0

    while True:
        now = datetime.now()

        # Create image for ONLY the top partial area (168 x PARTIAL_HEIGHT)
        partial_image = Image.new('1', (168, PARTIAL_HEIGHT), 255)
        p_draw = ImageDraw.Draw(partial_image)

        # Draw current time
        p_draw.text((10, 20), now.strftime('%H:%M'), font=font_large, fill=0)

        # Draw date
        p_draw.text((10, 80), now.strftime('%A'), font=font_medium, fill=0)
        p_draw.text((10, 110), now.strftime('%B %d'), font=font_medium, fill=0)

        # Draw update counter
        p_draw.text((10, 150), f"Updates: {update_count + 1}", font=font_small, fill=0)

        # Show seconds with animated dots
        dots = '•' * ((now.second % 4) + 1)
        p_draw.text((10, 170), dots, font=font_medium, fill=0)

        # Update only the partial area
        buffer = epd.getbuffer_partial(partial_image, PARTIAL_HEIGHT)

        update_start = time.time()
        epd.display_partial(buffer, PARTIAL_HEIGHT)
        duration = time.time() - update_start

        update_count += 1
        logging.info(f"[{update_count:3d}] {now.strftime('%H:%M:%S')} - "
                     f"Partial refresh: {duration:.1f}s")

        # Full refresh every 30 updates to clear ghosting from top area
        if update_count % 30 == 0:
            logging.info("      → Full refresh to clear ghosting from dynamic area...")

            # Redraw full screen
            full_image = Image.new('1', (168, 384), 255)
            draw = ImageDraw.Draw(full_image)

            # Separator
            draw.line((0, PARTIAL_HEIGHT, 168, PARTIAL_HEIGHT), fill=0, width=3)

            # Static content (unchanged)
            draw.text((10, STATIC_START + 20), "Status Board", font=font_medium, fill=0)
            draw.text((10, STATIC_START + 50), "Location: Office 2B", font=font_small, fill=0)
            draw.text((10, STATIC_START + 70), "ESL Display v2.0", font=font_small, fill=0)
            draw.text((10, STATIC_START + 100), "Partial Updates:", font=font_small, fill=0)
            draw.text((10, STATIC_START + 120), "Top area only", font=font_small, fill=0)

            # Current dynamic content
            draw.text((10, 20), now.strftime('%H:%M'), font=font_large, fill=0)
            draw.text((10, 80), now.strftime('%A'), font=font_medium, fill=0)
            draw.text((10, 110), now.strftime('%B %d'), font=font_medium, fill=0)
            draw.text((10, 150), f"Updates: {update_count}", font=font_small, fill=0)

            # Full refresh
            epd.init()
            epd.display(epd.getbuffer(full_image), None)

            # Reconfigure partial mode
            epd.init_partial(PARTIAL_HEIGHT)

        time.sleep(1)

except KeyboardInterrupt:
    logging.info("\n\n[STOPPED] User interrupted")
    logging.info(f"Total partial updates: {update_count}")
    logging.info("\nKey benefits demonstrated:")
    logging.info("1. Static content (bottom) stayed crisp throughout")
    logging.info("2. No ghosting accumulation on static elements")
    logging.info("3. Clear separation between dynamic and static areas")
    logging.info("\nCleaning up...")
    try:
        epd.init()
        epd.Clear()
        epd.sleep()
        logging.info("✓ Done")
    except Exception as e:
        logging.debug(f"Cleanup error: {e}")

except Exception as e:
    logging.error(f"\n[ERROR] {e}")
    import traceback

    traceback.print_exc()

finally:
    try:
        esl.module_exit()
    except Exception as e:
        logging.debug(f"Module exit error: {e}")