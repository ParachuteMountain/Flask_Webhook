from flask import Flask, request, Response, render_template, jsonify

from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_v1_5
import requests
import base64

app = Flask(__name__)

# encrypting secret using RSA PCKS
def getEncryptedText(rsaKey, secret):
    keyDER = base64.b64decode(rsaKey)
    keyPub = RSA.importKey(keyDER)
    cipherRSA = PKCS1_v1_5.new(keyPub)
    ciphertext = cipherRSA.encrypt(str.encode(secret))
    emsg = base64.b64encode(ciphertext)
    return emsg.decode()

@app.route('/')
def home():
    return jsonify(summary = {"Home": "Home v4"})

@app.route('/v0.5/patients/on-find', methods=['POST'])
def pat_on_find():
    print("Patient find received!")
    print(request.json)
    return jsonify(summary = {"Patient": "On Find"})

# SUBSCRIPTION REQUETS URLS
@app.route('/v0.5/subscription-requests/cm/on-init', methods=['POST'])
def sub_req_on_init():
    print("Sub Req on init received!")
    print(request.json)
    return jsonify(summary = {"Sub_Req": "On Init"})

# CONSENT RREQUEST URLs
@app.route('/v0.5/consent-requests/on-init', methods=['POST'])
def con_req_on_init():
    print("Con Req on init received!")
    print(request.json)
    return jsonify(summary = {"Con_Req": "On Init"})

@app.route('/v0.5/consent-requests/on-status', methods=['POST'])
def con_req_on_status():
    print("Con Req on status received!")
    print(request.json)
    return jsonify(summary = {"Con_Req": "On Status"})

@app.route('/encrypt-secret/<keyType>/<secret>', methods=['POST'])
def enc_secret(keyType, secret):
    print("Encrypting secret!")
    print(keyType)
    print(secret)

    url = None
    if keyType == "0":
        url = "https://healthidsbx.abdm.gov.in/api/v1/auth/cert"
    if keyType == "1":
        url = "https://phrbeta.abdm.gov.in:443/api/v1/phr/public/certificate"

    payload={}
    headers = {
    'Accept-Language': 'en-US'
    }
    response = requests.request("GET", url, headers=headers, data=payload)
    text = response.text
    public_key = text.replace('\n','').split('-----')[2]
    encrypted_secret = getEncryptedText(public_key, secret)

    print(encrypted_secret)
    # print(request.json)
    return jsonify({"encSecret": encrypted_secret})

if __name__ == '__main__':
    app.run(debug=True)
