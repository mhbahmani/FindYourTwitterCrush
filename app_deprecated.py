from flask import Flask, request
from flask import render_template

from image_generator import merge_images
from twitter_handler import Twitter


app = Flask(__name__)


# @app.route("/out", methods=["POST"])
@app.route("/")
def start():
    # res = request.form['text']
    # names = request.form['names']
    # avg = request.form['avg']
    avg = 76.6
    res = {'MGhasemi8156': 2, 'mohsenmortezaie': 2, 'MMoravveji': 2, 'iamggoonngg': 2, 'm_saleh_saeidi': 2, 'ab_zahraw': 2, 'baba_lengdraz': 2, 'Naz_Eliii': 2, 'AFarsangi': 2, 'armitajli': 2, 'mobiiinaaa': 2, 'SkySep999': 2, 'farida__qp': 3, 'A81829': 3, 'Milad123454321': 3, 'iamAMT1': 3, 'ghalbe_abi': 3, 'MehranMontazer': 3, 'Erf__Kha': 4, 'lunatic_amib': 5}
    names = ['MGhasemi8156', 'mohsenmortezaie', 'MMoravveji', 'iamggoonngg', 'm_saleh_saeidi', 'ab_zahraw', 'baba_lengdraz', 'Naz_Eliii', 'AFarsangi', 'armitajli', 'mobiiinaaa', 'SkySep999', 'farida__qp', 'A81829', 'Milad123454321', 'iamAMT1', 'ghalbe_abi', 'MehranMontazer', 'Erf__Kha', 'lunatic_amib']
    twitter_client = Twitter()
    items = []
    # res = res.strip("}")
    # res = res.strip("{")
    # res = res.replace('"', '')
    # res = res.replace("'", '')
    # res = dict(subs.split(": ") for subs in res.split(","))
    # names = names.strip("]")
    # names = names.strip("[")
    # names = names.replace('"', '')
    # names = names.replace("'", '')
    # names = list(subs for subs in names.split(", "))
    i = 0
    # names = list(reversed(names))
    l = list(reversed(list(res.items())[-12:]))
    items = [[5, 'lunatic_amib', 'http://pbs.twimg.com/profile_images/1627023157772054529/-RMzGzua.jpg', 'lunatic_amib'], [4, 'Erf__Kha', 'http://pbs.twimg.com/profile_images/1424349943700017158/ZVavxLxO.jpg', 'Erf__Kha'], [3, 'MehranMontazer', 'http://pbs.twimg.com/profile_images/1606339570173353984/kIbhlC3p.jpg', 'MehranMontazer'], [3, 'ghalbe_abi', 'http://pbs.twimg.com/profile_images/1616080056111202306/NiiNs3my.jpg', 'ghalbe_abi'], [3, 'iamAMT1', 'http://pbs.twimg.com/profile_images/1628855496412102656/oQmQr062.jpg', 'iamAMT1'], [3, 'Milad123454321', 'http://pbs.twimg.com/profile_images/1261047570333405186/FGd75LF4.jpg', 'Milad123454321'], [3, 'A81829', 'http://pbs.twimg.com/profile_images/1439595648878272525/qCtkEj1d.jpg', 'A81829'], [3, 'farida__qp', 'http://pbs.twimg.com/profile_images/1562369411809509376/jLcOILIC.jpg', 'farida__qp'], [2, 'SkySep999', 'http://pbs.twimg.com/profile_images/1614362795520180226/kb5GJCtc.jpg', 'SkySep999'], [2, 'mobiiinaaa', 'http://pbs.twimg.com/profile_images/1588796368071557120/fIVDD8O9.jpg', 'mobiiinaaa'], [2, 'armitajli', 'http://pbs.twimg.com/profile_images/1606269624701550592/wS7BlzY_.jpg', 'armitajli'], [2, 'AFarsangi', 'http://pbs.twimg.com/profile_images/1573223251949637635/y8pBBKMB.jpg', 'AFarsangi']]
    # for user, val in l:
    #     i += 1
    #     items.append([val, user, twitter_client.get_user_profile_image(user).replace("_normal", ""), names[-i]])
    # print(items)
    # html = render_template('results.html', items1=items[:6], items2=items[6:12], avg=avg)
    merge_images(items)
    # from htmlwebshot import WebShot
    # shot = WebShot()
    # shot.create_pic(html=html, output="./out.jpg")
    return "gooood"