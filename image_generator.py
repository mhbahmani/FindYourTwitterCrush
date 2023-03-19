from PIL import Image
from PIL import ImageDraw, ImageFont

import requests
import random
import string
import os


OUTPUT_DIR="merged_images"

NUM_ROWS = 2
IMAGE_BORDER = 300


def merge_images(data: list, avg: float):
    TOTAL_IMAGES = len(data)

    PROFILE_IMAGES_DISTANCE = 20
    PROFILE_IMAGES_DISTANCE_X = int(IMAGE_BORDER / (TOTAL_IMAGES / NUM_ROWS))
    PROFILE_IMAGES_DISTANCE_Y = int(IMAGE_BORDER / NUM_ROWS)

    image_urls = [person[2] for person in data]
    key = download_image(image_urls)
    # key = "H4WC6ZDFY3"

    images = []
    images_location = [(PROFILE_IMAGES_DISTANCE_X, PROFILE_IMAGES_DISTANCE)]
    for i in range(len(data)):
        if i != 0 and i <= 5:
            images_location.append((i * images[i-1].size[0] + (i+1) * PROFILE_IMAGES_DISTANCE_X, PROFILE_IMAGES_DISTANCE))
        elif i > 5:
            images_location.append(((i-6) * images[i-1].size[0] + (i-5) * PROFILE_IMAGES_DISTANCE_X, images[i-1].size[1] + PROFILE_IMAGES_DISTANCE_Y + 20))
        image = Image.open(f"images/{key}-{i}.jpg")
        image = image.resize((426, 420))
        images.append(image)

    #resize, first image
    images_size = images[0].size

    X = int(TOTAL_IMAGES/NUM_ROWS) * images_size[0] + IMAGE_BORDER + PROFILE_IMAGES_DISTANCE_X
    Y = NUM_ROWS * images_size[1] + IMAGE_BORDER + 100
    
    merged_image = Image.new('RGB',(X, Y), (250,250,250))
    for i in range(len(images)):
        merged_image.paste(images[i], images_location[i])
    
    font = ImageFont.truetype("baloo.ttf", 40)
    image_draw = ImageDraw.Draw(merged_image)
    for i in range(len(images)):
        # Write account name and score under the image
        image_draw.text((images_location[i][0] + 10, images_location[i][1] + 450), f"{data[i][3]} - {data[i][0]}%", fill=(0,0,0), font=font)

    font = ImageFont.truetype("baloo.ttf", 60)
    # Write average score in the buttom middle of the image
    image_draw.text((X/2 - 100, Y - 100), f"Average: {avg}%", fill=(0,0,0), font=font)

    merged_image.paste(images[i],(images_size[0],0))
    merged_image.save(f"{OUTPUT_DIR}/{key}-merged.jpg","JPEG")
    
    # merged_image.show()
    cleanup_image(key, TOTAL_IMAGES)

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
