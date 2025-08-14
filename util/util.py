import os

from PIL import Image
import numpy as np
import pyfiglet

# Path to your robot logo
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_PATH = os.path.join(BASE_DIR, 'img\\TechNoisePresentationLogo.png')

# ASCII characters from dark to light
ASCII_CHARS = "@%#*+=-:. "

# Resize image for ASCII output
def resize_image(image, new_width=80):
    width, height = image.size
    aspect_ratio = height / width
    new_height = int(aspect_ratio * new_width * 0.55)  # Adjust for font aspect ratio
    return image.resize((new_width, new_height))

# Map pixels to ASCII
def pixel_to_ascii(image):
    pixels = np.array(image)
    ascii_image = ""
    for row in pixels:
        for pixel in row:
            r, g, b = pixel[:3]
            brightness = (0.299*r + 0.587*g + 0.114*b) / 255
            char = ASCII_CHARS[int(brightness * (len(ASCII_CHARS) - 1))]
            ascii_image += f"\x1b[38;2;{r};{g};{b}m{char}\x1b[0m"
        ascii_image += "\n"
    return ascii_image

def plus_figlet(text):
    """Render text as ASCII art using '+' for filled areas."""
    ascii_text = pyfiglet.figlet_format(text, font="banner")  # You can choose other fonts
    return ascii_text

def print_startup_banner():
    # Load and process image
    image = Image.open(IMAGE_PATH).convert("RGB")
    image = resize_image(image, new_width=80)
    ascii_img = pixel_to_ascii(image)

    # Print ASCII robot
    print(ascii_img)

    # Print ASCII-art tagline in orange
    ascii_tagline = plus_figlet("Hear the future")
    orange_ascii_tagline = "\x1b[38;2;255;102;0m" + ascii_tagline + "\x1b[0m"
    print(orange_ascii_tagline)

