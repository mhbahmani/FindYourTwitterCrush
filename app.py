from flask import Flask, request
from flask import render_template


app = Flask(__name__)


@app.route("/")
def get_result():
    return render_template("index.html")


@app.route("/out", methods=["POST"])
def start():
    res = request.form['text']
    names = request.form['names']
    avg = request.form['avg']
    twitter_client = Twitter()
    items = []
    res = res.strip("}")
    res = res.strip("{")
    res = res.replace('"', '')
    res = res.replace("'", '')
    res = dict(subs.split(": ") for subs in res.split(","))
    names = names.strip("]")
    names = names.strip("[")
    names = names.replace('"', '')
    names = names.replace("'", '')
    names = list(subs for subs in names.split(", "))
    i = 0
    # names = list(reversed(names))
    l = list(reversed(list(res.items())[-12:]))
    for user, val in l:
        i += 1
        items.append([val, user, twitter_client.get_user_profile_image(user).replace("_normal", ""), names[-i]])
    return render_template('results.html', items1=items[:5], items2=items[5:12], avg=avg)
