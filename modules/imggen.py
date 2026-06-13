import io

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps


def downloadImage(url):
    response = requests.get(url)
    imagebytes = io.BytesIO(response.content)

    return Image.open(imagebytes)


def create_circular_image(image):
    # 1. Open the image
    img = image

    # 2. Square the image based on its shortest side (so the circle isn't skewed)
    size = min(img.size)
    img = ImageOps.fit(img, (70, 70), centering=(0.5, 0.5))

    # 3. Create a blank grayscale image for the mask
    mask = Image.new("L", (70, 70), 0)
    draw = ImageDraw.Draw(mask)

    # 4. Draw a solid white circle on the mask
    draw.ellipse((0, 0, 70, 70), fill=255)

    # 5. Apply the mask to the image's alpha channel
    result = img.copy()
    result.putalpha(mask)

    return result


font = ImageFont.truetype("roboto.ttf", size=20)


def generateImage(profileURL, level, xp, max_xp, name):

    if profileURL is None:
        profile = Image.new("RGBA", (50, 50), color=(27, 27, 27))
        canvas2 = ImageDraw.Draw(profile)
        canvas2.text((20, 12), "?", (255, 255, 255), font=font)
    else:
        profile = downloadImage(profileURL)

    profileImg = create_circular_image(profile)

    # image initialization
    img = Image.new("RGB", (450, 150), color=(43, 43, 43))
    canvas = ImageDraw.Draw(img)

    percentage = xp / max_xp
    max_s = max(75, 50 + 350 * percentage)

    # drawing
    img.paste(profileImg, (15, 15), mask=profileImg)
    canvas.circle((50, 50), 35, fill=None, outline=(255, 255, 255), width=5)
    canvas.rounded_rectangle((75, 100, 400, 125), 10, (108, 108, 108))
    canvas.rounded_rectangle((75, 100, max_s, 125), 10, (106, 201, 111))
    canvas.text((300, 10), f"Level {level}", (255, 255, 255), font=font)
    canvas.text((300, 30), f"XP: {xp}/{max_xp}", (255, 255, 255), font=font)
    canvas.text((85, 75), name, (255, 255, 255), font=font)

    # create raw binary
    image_binary = io.BytesIO()
    img.save(image_binary, format="PNG")
    image_binary.seek(0)

    return image_binary
