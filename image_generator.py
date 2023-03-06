from PIL import Image
import requests
import random
import string

TOTAL_IMAGES = 10
NUM_ROWS = 2

IMAGE_BORDER = 300
PROFILE_IMAGES_DISTANCE = 20
PROFILE_IMAGES_DISTANCE_X = int(IMAGE_BORDER / (TOTAL_IMAGES / NUM_ROWS))
PROFILE_IMAGES_DISTANCE_Y = int(IMAGE_BORDER / NUM_ROWS)

def merge_images(data: list):
    image_urls = [person[2] for person in data]
    key = download_image(image_urls)
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
    merged_image = Image.new('RGB',(int(TOTAL_IMAGES/NUM_ROWS) * images_size[0] + IMAGE_BORDER + PROFILE_IMAGES_DISTANCE_X, NUM_ROWS * images_size[1] + IMAGE_BORDER), (250,250,250))
    for i in range(len(images)):
        merged_image.paste(images[i], images_location[i])

    # merged_image.paste(images[i],(images_size[0],0))
    merged_image.save(f"images/{key}-merged.jpg","JPEG")
    # merged_image.show()

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
