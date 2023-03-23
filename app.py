from flask import Flask, request
from decouple import config
import tweepy


app = Flask(__name__)

# Callback flask app



@app.route('/callback', methods=['GET', 'POST'])
def print_all_request_data():
    # Get args oauth_token and oauth_verifier
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')
    save_tokens_in_file(oauth_token, oauth_verifier)
    return "OK"


def save_tokens_in_file(oauth_token, oauth_verifier):
    with open("oauth_tokens.txt", "w") as f:
        f.write(f"{oauth_token} {oauth_verifier}")

def load_tokens_from_file():
    with open("oauth_token.txt", "r") as f:
        return f.read().split(" ")