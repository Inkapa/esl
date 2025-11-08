#!/usr/bin/python
# -*- coding:utf-8 -*-

import logging
import esl
import sys
import os
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple, Optional

logging.basicConfig(level=logging.DEBUG)

# Display dimensions
DISPLAY_WIDTH = 168
DISPLAY_HEIGHT = 384
MARGIN = 10  # Pixel margin from edges


def find_available_font() -> Optional[str]:
    """
    Try to find an available TrueType font on the system.

    Returns:
        Path to font file, or None if no font found
    """
    # List of common font paths to try
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            logging.info(f"Found font: {font_path}")
            return font_path

    logging.warning("No TrueType fonts found, will use PIL default font")
    return None


def calculate_optimal_font_size(text: str, width: int, height: int,
                                font_path: Optional[str] = None,
                                min_size: int = 10, max_size: int = 200) -> Tuple[ImageFont.ImageFont, int]:
    """
    Calculate the optimal font size to fit text within given dimensions.

    Uses binary search to find the largest font size that fits the text
    within the specified width and height constraints.
    """

    # Check if we can use TrueType fonts
    use_truetype = font_path is not None and os.path.exists(font_path)

    if not use_truetype:
        logging.warning("Using PIL default font (not scalable)")
        default_font = ImageFont.load_default()
        return default_font, 10  # Default font is roughly size 10

    def get_text_dimensions(font: ImageFont.ImageFont, text: str,
                            max_width: int) -> Tuple[int, int]:
        """Calculate text dimensions with word wrapping."""
        dummy_img = Image.new('1', (1, 1))
        draw = ImageDraw.Draw(dummy_img)

        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_width = bbox[2] - bbox[0]

            if line_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Single word too long, add it anyway
                    lines.append(word)

        if current_line:
            lines.append(' '.join(current_line))

        # Calculate total height
        total_height = 0
        max_line_width = 0

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_height = bbox[3] - bbox[1]
            line_width = bbox[2] - bbox[0]
            total_height += line_height
            max_line_width = max(max_line_width, line_width)

        # Add spacing between lines (approximate line height * 0.2)
        if len(lines) > 1:
            line_spacing = int((total_height / len(lines)) * 0.2)
            total_height += line_spacing * (len(lines) - 1)

        return max_line_width, total_height

    # Binary search for optimal font size
    low, high = min_size, max_size
    best_size = min_size

    while low <= high:
        mid = (low + high) // 2

        font = ImageFont.truetype(font_path, mid)
        text_width, text_height = get_text_dimensions(font, text, width)

        if text_width <= width and text_height <= height:
            best_size = mid
            low = mid + 1
        else:
            high = mid - 1

    final_font = ImageFont.truetype(font_path, best_size)
    return final_font, best_size


def draw_wrapped_text(draw: ImageDraw.ImageDraw, text: str,
                      font: ImageFont.ImageFont,
                      width: int, height: int) -> None:
    """
    Draw text with word wrapping, centered on the canvas.
    """
    words = text.split()
    lines = []
    current_line = []

    # Word wrap
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]

        if line_width <= width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)

    if current_line:
        lines.append(' '.join(current_line))

    # Calculate positions for vertical centering
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_heights.append(bbox[3] - bbox[1])

    # Line spacing
    avg_line_height = sum(line_heights) / len(line_heights) if line_heights else 0
    line_spacing = int(avg_line_height * 0.2)
    total_height = sum(line_heights) + line_spacing * (len(lines) - 1)

    # Start y position (centered)
    y = (height - total_height) // 2

    # Draw each line
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x = (width - line_width) // 2  # Center horizontally

        draw.text((x, y), line, font=font, fill=0)
        y += line_heights[i] + line_spacing


def display_text(text: str, orientation: str = "portrait", color: str = "black") -> None:
    """
    Display text on the e-ink screen with automatic font sizing.

    Args:
        text: Text to display
        orientation: "portrait" (168x384) or "landscape" (384x168)
        color: "black" or "red" for text color
    """
    # Find available font
    font_path = find_available_font()

    # Determine image dimensions based on orientation
    if orientation.lower() == "landscape":
        img_width = DISPLAY_HEIGHT  # 384
        img_height = DISPLAY_WIDTH  # 168
        logging.info("Using LANDSCAPE orientation (384x168)")
    else:
        img_width = DISPLAY_WIDTH  # 168
        img_height = DISPLAY_HEIGHT  # 384
        logging.info("Using PORTRAIT orientation (168x384)")

    # Calculate optimal font size
    logging.info(f"Calculating optimal font size for: '{text}'")
    usable_width = img_width - (2 * MARGIN)
    usable_height = img_height - (2 * MARGIN)

    font, font_size = calculate_optimal_font_size(
        text, usable_width, usable_height, font_path
    )
    logging.info(f"Using font size: {font_size} in {color.upper()} color")

    # Create image
    image = Image.new('1', (img_width, img_height), 1)  # White background
    draw = ImageDraw.Draw(image)

    # Draw text
    draw_wrapped_text(draw, text, font, usable_width, usable_height)

    # Initialize display
    epd = esl.EPD()
    logging.info("Initializing display...")
    epd.init()

    # Prepare buffers based on color choice
    buffer = epd.getbuffer(image)

    # Create a white buffer (all 0xFF) to clear the unused layer
    white_buffer = [0xFF] * len(buffer)

    if color.lower() == "red":
        # Red text: put text in red buffer, clear black buffer
        logging.info("Displaying RED text on e-ink screen (one-time refresh)...")
        epd.display(white_buffer, buffer)
    else:
        # Black text: put text in black buffer, clear red buffer
        logging.info("Displaying BLACK text on e-ink screen (one-time refresh)...")
        epd.display(buffer, white_buffer)

    logging.info("Display complete. Entering sleep mode...")
    epd.sleep()


def main():
    """Main entry point for the script."""
    print("\n=== E-Ink Text Display ===\n")

    # Get orientation
    orientation = input("Choose orientation (portrait/landscape) [portrait]: ").strip().lower()
    if not orientation:
        orientation = "portrait"

    if orientation not in ["portrait", "landscape"]:
        print(f"Invalid orientation '{orientation}', defaulting to portrait")
        orientation = "portrait"

    # Get color
    color = input("Choose text color (black/red) [black]: ").strip().lower()
    if not color:
        color = "black"

    if color not in ["black", "red"]:
        print(f"Invalid color '{color}', defaulting to black")
        color = "black"

    # Get text
    if len(sys.argv) > 1:
        text = ' '.join(sys.argv[1:])
    else:
        text = input("Enter text to display: ").strip()

    if not text:
        logging.error("No text provided!")
        sys.exit(1)

    try:
        display_text(text, orientation, color)
        logging.info("✓ Success!")

    except IOError as e:
        logging.error(f"IO Error: {e}")

    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        esl.module_exit()

    except Exception as e:
        logging.error(f"Error: {e}")
        esl.module_exit()


if __name__ == "__main__":
    main()