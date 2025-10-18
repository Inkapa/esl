# ESL E-Ink Display Driver

Python driver for GDisplay e-ink screens taken from Imagotag SES ESLs (168×384, tri-color) on Raspberry Pi.

This uses a Waveshare SPI HAT, but it should work with any universal E-Ink HAT.

## Installation

```bash
sudo apt-get update
sudo apt-get install python3-pip
sudo apt-get install python3-pil
sudo apt-get install python3-numpy
sudo pip3 install spidev
sudo apt install python3-gpiozero
```

## Usage

```python
import esl

epd = esl.EPD()
epd.init()

# Seperate colour values with Floyd–Steinberg dithering
HBlack, HRed = epd.separate_colors('photo.jpg', use_dithering=True)
epd.display(epd.getbuffer(HBlack), epd.getbuffer(HRed))

epd.sleep()
```


## Credits

Based on work by [Waveshare Team](https://github.com/waveshareteam/e-Paper)

## License

MIT
