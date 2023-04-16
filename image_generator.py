from PIL import Image
from PIL import ImageDraw, ImageFont

from messages import MOST_LIKING_USERS_TITLE, MOST_LIKED_USERS_TITLE

import langdetect

import requests
import logging
import random
import string
import os


OUTPUT_DIR="merged_images"

NUM_ROWS = 2
IMAGE_BORDER = 300

IMAGE_X = 426
IMAGE_Y = 420


def merge_images(data: list, avg: float = -1, username: str = None, total_likes: int = -1):
    TOTAL_IMAGES = len(data)

    TITLE_LINE_LENGTH = 120

    PROFILE_IMAGES_DISTANCE = 20
    PROFILE_IMAGES_DISTANCE_X = int(IMAGE_BORDER / (TOTAL_IMAGES / NUM_ROWS))
    PROFILE_IMAGES_DISTANCE_Y = int(IMAGE_BORDER / NUM_ROWS)

    image_urls = [person[2] for person in data]
    key = download_image(image_urls)
    # key = "VZUCJ8ZQYD"

    images = []
    images_location = [(PROFILE_IMAGES_DISTANCE_X, PROFILE_IMAGES_DISTANCE + TITLE_LINE_LENGTH)]
    for i in range(len(data)):
        if i != 0 and i <= 5:
            images_location.append((i * images[i-1].size[0] + (i+1) * PROFILE_IMAGES_DISTANCE_X, PROFILE_IMAGES_DISTANCE + TITLE_LINE_LENGTH))
        elif i > 5:
            images_location.append(((i-6) * images[i-1].size[0] + (i-5) * PROFILE_IMAGES_DISTANCE_X, images[i-1].size[1] + PROFILE_IMAGES_DISTANCE_Y + 20 + TITLE_LINE_LENGTH))
        image = Image.open(f"images/{key}-{i}.jpg")
        image = image.resize((IMAGE_X, IMAGE_Y))
        images.append(image)

    #resize, first image
    images_size = images[0].size

    X = int(TOTAL_IMAGES/NUM_ROWS) * images_size[0] + IMAGE_BORDER + PROFILE_IMAGES_DISTANCE_X
    Y = NUM_ROWS * images_size[1] + IMAGE_BORDER + TITLE_LINE_LENGTH
    Y += 100 # for average and total likes  

    merged_image = Image.new('RGB',(X, Y), (250,250,250))
    title = MOST_LIKING_USERS_TITLE if avg != -1 else MOST_LIKED_USERS_TITLE
    font = ImageFont.truetype("kamran.ttf", 70)
    image_draw = ImageDraw.Draw(merged_image)
    image_draw.text((X/2 - len(title) / 2 * 20, TITLE_LINE_LENGTH / 2 - 20), title, fill=(0,0,0), font=font)
    for i in range(len(images)):
        # paste images with circular mask
        mask = Image.new('L', images[i].size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + images[i].size, fill=255)
        merged_image.paste(images[i], images_location[i], mask)
    
    en_font = ImageFont.truetype("baloo.ttf", 40)
    pr_font = ImageFont.truetype("kamran.ttf", 50)
    image_draw = ImageDraw.Draw(merged_image)
    template_text = "{} - {}%" if avg != -1 else "{} - {}"
    for i in range(len(images)):
        # Write account name and score middle of the image
        if avg == -1:
            text = template_text.format(data[i][1], data[i][0])
        else:
            text = template_text.format(data[i][1], '{:.1f}'.format(data[i][0]))
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

    font = ImageFont.truetype("baloo.ttf", 60)
    if avg != -1:
        # Write average score in the buttom middle of the image
        image_draw.text((X/2 - 170, Y - 100), f"Average: {'{:.1f}'.format(avg)}", fill=(0,0,0), font=font)
    if total_likes != -1: 
        image_draw.text((X/2 - 200, Y - 100), f"Total likes: {total_likes}", fill=(0,0,0), font=font)

    if avg != -1:
        output_path = f"{OUTPUT_DIR}/{username}-liking.jpg"
    else:
        output_path = f"{OUTPUT_DIR}/{username}-liked.jpg"
    merged_image.save(output_path,"JPEG")

    # merged_image.show()
    cleanup_image(key, TOTAL_IMAGES)
    return output_path


def download_image(images: list):
    # generate a random key
    key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
    counter = 0
    for image in images:
        try:
            response = requests.get(image)
            content = response.content
        except Exception as e:
            logging.error(e)
            logging.info("Using default image as profile image, image liks:", image)
            content = open("templates/default-profile-image.jpg", "rb").read()
        with open(f"images/{key}-{counter}.jpg", "wb") as f:
            f.write(content)
        counter += 1
    return key


def cleanup_image(key: str, TOTAL_IMAGES: int):
    for i in range(TOTAL_IMAGES):
        os.remove(f"images/{key}-{i}.jpg")


def retrieve_image_path(username: str, type: str):
    if type == "liking":
        path = f"{OUTPUT_DIR}/{username}-liking.jpg"
        if os.path.exists(path):
            return path
    elif type == "liked":
        path = f"{OUTPUT_DIR}/{username}-liked.jpg"
        if os.path.exists(path):
            return path

# items = [[5, 'lunatic_amib', 'http://pbs.twimg.com/profile_images/1627023157772054529/-RMzGzua.jpg', '*فارسی'], [4, 'Erf__Kha', 'https://pbs.twimg.com/profile_images/1636885496835063808/CcVomPqU_400x400.jpg', 'لاس نزن انقد'], [3, 'MehranMontazer', 'http://pbs.twimg.com/profile_images/1606339570173353984/kIbhlC3p.jpg', 'MehranMontazer'], [3, 'ghalbe_abi', 'http://pbs.twimg.com/profile_images/1616080056111202306/NiiNs3my.jpg', 'ghalbe_abi'], [3, 'iamAMT1', 'http://pbs.twimg.com/profile_images/1628855496412102656/oQmQr062.jpg', 'iamAMT1'], [3, 'Milad123454321', 'http://pbs.twimg.com/profile_images/1261047570333405186/FGd75LF4.jpg', 'Milad123454321'], [3, 'A81829', 'http://pbs.twimg.com/profile_images/1439595648878272525/qCtkEj1d.jpg', 'A81829'], [3, 'farida__qp', 'http://pbs.twimg.com/profile_images/1562369411809509376/jLcOILIC.jpg', 'لاس کار بدیه'], [2, 'SkySep999', 'http://pbs.twimg.com/profile_images/1614362795520180226/kb5GJCtc.jpg', 'SkySep999'], [2, 'mobiiinaaa', 'https://pbs.twimg.com/profile_images/1636817146780041216/Sk2KHU-x_400x400.jpg', 'mobiiinaaa'], [2, 'armitajli', 'http://pbs.twimg.com/profile_images/1606269624701550592/wS7BlzY_.jpg', 'armitajli'], [2, 'AFarsangi', 'http://pbs.twimg.com/profile_images/1573223251949637635/y8pBBKMB.jpg', 'AFarsangi']]
# merge_images(items, total_likes=2100)
