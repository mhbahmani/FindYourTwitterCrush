from PIL import Image
from PIL import ImageDraw, ImageFont
import langdetect

import requests
import random
import string
import os


OUTPUT_DIR="merged_images"

NUM_ROWS = 2
IMAGE_BORDER = 300

IMAGE_X = 426
IMAGE_Y = 420

def merge_images(data: list, avg: float = -1, username: str = None):
    TOTAL_IMAGES = len(data)

    PROFILE_IMAGES_DISTANCE = 20
    PROFILE_IMAGES_DISTANCE_X = int(IMAGE_BORDER / (TOTAL_IMAGES / NUM_ROWS))
    PROFILE_IMAGES_DISTANCE_Y = int(IMAGE_BORDER / NUM_ROWS)

    image_urls = [person[2] for person in data]
    key = download_image(image_urls)
    # key = "3WVXNA6QMH"

    images = []
    images_location = [(PROFILE_IMAGES_DISTANCE_X, PROFILE_IMAGES_DISTANCE)]
    for i in range(len(data)):
        if i != 0 and i <= 5:
            images_location.append((i * images[i-1].size[0] + (i+1) * PROFILE_IMAGES_DISTANCE_X, PROFILE_IMAGES_DISTANCE))
        elif i > 5:
            images_location.append(((i-6) * images[i-1].size[0] + (i-5) * PROFILE_IMAGES_DISTANCE_X, images[i-1].size[1] + PROFILE_IMAGES_DISTANCE_Y + 20))
        image = Image.open(f"images/{key}-{i}.jpg")
        image = image.resize((IMAGE_X, IMAGE_Y))
        images.append(image)

    #resize, first image
    images_size = images[0].size

    X = int(TOTAL_IMAGES/NUM_ROWS) * images_size[0] + IMAGE_BORDER + PROFILE_IMAGES_DISTANCE_X
    Y = NUM_ROWS * images_size[1] + IMAGE_BORDER
    if avg != -1: Y += 100
    
    merged_image = Image.new('RGB',(X, Y), (250,250,250))
    for i in range(len(images)):
        merged_image.paste(images[i], images_location[i])
    
    en_font = ImageFont.truetype("baloo.ttf", 40)
    pr_font = ImageFont.truetype("kamran.ttf", 50)
    image_draw = ImageDraw.Draw(merged_image)
    template_text = "{} - {}%" if avg != -1 else "{} - {}"
    for i in range(len(images)):
        # Write account name and score middle of the image
        text = template_text.format(data[i][1], data[i][0])
        image_draw.text((images_location[i][0] + 10 + int(IMAGE_X / 2 - len(text) / 2 * 22), images_location[i][1] + 430), text, fill=(0,0,0), font=en_font)
        # Write account name in the next line
        # print(data[i][3])
        try:
            if langdetect.detect(data[i][3]) == "fa" or langdetect.detect(data[i][3]) == "ar":
                image_draw.text((images_location[i][0] + 10 + int(IMAGE_X / 2 - len(data[i][3]) / 2 * 17), images_location[i][1] + 480), f"{data[i][3]}", fill=(0,0,0), font=pr_font)
            else:
                image_draw.text((images_location[i][0] + 10 + int(IMAGE_X / 2 - len(data[i][3]) / 2 * 25), images_location[i][1] + 480), f"{data[i][3]}", fill=(0,0,0), font=en_font)
        except:
            image_draw.text((images_location[i][0] + 10 + int(IMAGE_X / 2 - len(data[i][3]) / 2 * 25), images_location[i][1] + 480), f"{data[i][3]}", fill=(0,0,0), font=en_font)

    if avg != -1:
        font = ImageFont.truetype("baloo.ttf", 60)
        # Write average score in the buttom middle of the image
        image_draw.text((X/2 - 100, Y - 100), f"Average: {avg}%", fill=(0,0,0), font=font)

    output_path = f"{OUTPUT_DIR}/{username}-{key}-merged.jpg"
    merged_image.save(output_path,"JPEG")

    # merged_image.show()
    cleanup_image(key, TOTAL_IMAGES)
    return output_path


def download_image(images: list):
    # generate a random key
    key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
    counter = 0
    for image in images:
        response = requests.get(image)
        with open(f"images/{key}-{counter}.jpg", "wb") as f:
            f.write(response.content)
        counter += 1
    return key


def cleanup_image(key: str, TOTAL_IMAGES: int):
    for i in range(TOTAL_IMAGES):
        os.remove(f"images/{key}-{i}.jpg")


# items = [[5, 'lunatic_amib', 'http://pbs.twimg.com/profile_images/1627023157772054529/-RMzGzua.jpg', '*فارسی'], [4, 'Erf__Kha', 'http://pbs.twimg.com/profile_images/1424349943700017158/ZVavxLxO.jpg', 'لاس نزن انقد'], [3, 'MehranMontazer', 'http://pbs.twimg.com/profile_images/1606339570173353984/kIbhlC3p.jpg', 'MehranMontazer'], [3, 'ghalbe_abi', 'http://pbs.twimg.com/profile_images/1616080056111202306/NiiNs3my.jpg', 'ghalbe_abi'], [3, 'iamAMT1', 'http://pbs.twimg.com/profile_images/1628855496412102656/oQmQr062.jpg', 'iamAMT1'], [3, 'Milad123454321', 'http://pbs.twimg.com/profile_images/1261047570333405186/FGd75LF4.jpg', 'Milad123454321'], [3, 'A81829', 'http://pbs.twimg.com/profile_images/1439595648878272525/qCtkEj1d.jpg', 'A81829'], [3, 'farida__qp', 'http://pbs.twimg.com/profile_images/1562369411809509376/jLcOILIC.jpg', 'لاس کار بدیه'], [2, 'SkySep999', 'http://pbs.twimg.com/profile_images/1614362795520180226/kb5GJCtc.jpg', 'SkySep999'], [2, 'mobiiinaaa', 'http://pbs.twimg.com/profile_images/1588796368071557120/fIVDD8O9.jpg', 'mobiiinaaa'], [2, 'armitajli', 'http://pbs.twimg.com/profile_images/1606269624701550592/wS7BlzY_.jpg', 'armitajli'], [2, 'AFarsangi', 'http://pbs.twimg.com/profile_images/1573223251949637635/y8pBBKMB.jpg', 'AFarsangi']]
# merge_images(items, 3.2)