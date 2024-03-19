from PIL import Image
from PIL import ImageDraw, ImageFont

from src.messages import MOST_LIKING_USERS_TITLE, MOST_LIKED_USERS_TITLE

import langdetect

import requests
import logging
import random
import string
import os


OUTPUT_DIR = "merged_images"
OUTPUT_WEB_SERVER_DIR = "static/merged_images"

FA_FONT_PATH = "templates/kamran.ttf"
EN_FONT_PATH = "templates/baloo.ttf"

NUM_ROWS = 2
IMAGE_BORDER = 300

IMAGE_X = 426
IMAGE_Y = 420


def merge_images(data: list, likes_avg: float = -1, username: str = None, total_likes: int = -1, private: bool = False) -> str:
    """
    Output: Path of the merged image
    """
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

    title = MOST_LIKING_USERS_TITLE if likes_avg != -1 else MOST_LIKED_USERS_TITLE
    font = ImageFont.truetype(FA_FONT_PATH, 70)
    image_draw = ImageDraw.Draw(merged_image)
    image_draw.text((X/2 - len(title) / 2 * 20, TITLE_LINE_LENGTH / 2 - 20), title, fill=(0,0,0), font=font)
    for i in range(len(images)):
        # paste images with circular mask
        mask = Image.new('L', images[i].size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + images[i].size, fill=255)
        merged_image.paste(images[i], images_location[i], mask)
    
    en_font = ImageFont.truetype(EN_FONT_PATH, 40)
    pr_font = ImageFont.truetype(FA_FONT_PATH, 50)
    image_draw = ImageDraw.Draw(merged_image)
    template_text = "{} - {}%" if likes_avg != -1 else "{} - {}"
    for i in range(len(images)):
        # Write account name and score middle of the image
        if likes_avg == -1:
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

    font = ImageFont.truetype(EN_FONT_PATH, 60)
    if likes_avg != -1:
        # Write average score in the buttom middle of the image
        image_draw.text((X/2 - 170, Y - 100), f"Average: {'{:.1f}'.format(likes_avg)}", fill=(0,0,0), font=font)
    if total_likes != -1: 
        image_draw.text((X/2 - 200, Y - 100), f"Total likes: {total_likes}", fill=(0,0,0), font=font)

    output_path = retrieve_image_path(username, "liking" if likes_avg != -1 else "liked", private)

    merged_image.save(output_path, "JPEG")

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


def retrieve_image_path(username: str, type: str, private: bool = False):
    username = username.lower()
    if type == "liking":
        if not private:
            return f"{OUTPUT_DIR}/{username}-liking.jpg"
        # Add a random string as key to the file name to prevent some one access to the file by guessing the file name
        return f"{OUTPUT_WEB_SERVER_DIR}/{username}-liking-{''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(50))}.jpg"
    elif type == "liked":
        if not private:
            return f"{OUTPUT_DIR}/{username}-liked.jpg"
        # Add a random string as key to the file name to prevent some one access to the file by guessing the file name
        return f"{OUTPUT_WEB_SERVER_DIR}/{username}-liked-{''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(50))}.jpg"

def check_output_image_is_present(username: str, type: str) -> str:
    path = retrieve_image_path(username, type)
    if os.path.exists(path):
        return path
    else:
        path = retrieve_image_path(username.lower(), type)
        return path if os.path.exists(path) else None