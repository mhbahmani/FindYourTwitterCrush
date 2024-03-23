The code is a mess, don't judge me :)  
I can do better :)

``` 
pip install -r requirements.txt

mkdir images
mkdir merged_images
mkdir -p statics/merged_images

# Set the tweet id
python main_listener.py

# Set the ACTION variable
python main_events_handler.py

# Start telegram bot
python main_telegram_handler.py

# Make this index on database
echo 'db.telegram_users.createIndex({"user_id": 1}, {unique: true})' | mongo twitter
```
