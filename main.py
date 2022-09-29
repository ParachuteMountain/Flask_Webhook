from flask import Flask, request, Response, render_template, jsonify

from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_v1_5
import requests
import uuid
import datetime
import json
import base64

app = Flask(__name__)

# BASE URLs
MAIN_URL = "https://dev.abdm.gov.in"
GATEWAY_HOST = f"{MAIN_URL}/gateway"
CM_URL = f"{MAIN_URL}/cm"

# -------------------- RUN FOR AUTH TOKEN --------------------#
@app.route('/get-token', methods=['GET'])
def get_gateway_token():
    print("-- GATEWAY TOKEN GET! --")

    sessions_url = f"{GATEWAY_HOST}/v0.5/sessions"
    payload = json.dumps({
        "clientId": "SBX_002007",
        "clientSecret": "00df942f-402b-4c85-87d4-92e99120f94c"
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', sessions_url, headers=headers, data=payload)
    global GATEWAY_AUTH_TOKEN
    GATEWAY_AUTH_TOKEN = f"Bearer {response.json()['accessToken']}"

    return response.json()
# TOKENS - set when Request called to this base
GATEWAY_AUTH_TOKEN = f"Bearer {get_gateway_token()['accessToken']}"

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
    return jsonify(summary = {"Home": "Home v8"})

# ---------------------------- HIP ---------------------------#
#   PATIENT INITIATED LINKING
@app.route('/v0.5/care-contexts/discover', methods=['POST'])
def care_cont_disc():
    print("HIP LOG: Care contexts discovery received!")
    print(request.json)

    # first do some searching in the HRP itself based on request.json data information
    # Get the care contexts for the patient using Fuzzy Match
    # Check: F:\AbPt_ABDM\Theoretical_Info\FHIR\CC+FHIR\HIP_CC file
    # Give patient info if found (even with 0 CC) else if there were errors addd to error

    # we must reply with on-discover as an HIP
    cbl_url = f"{GATEWAY_HOST}/v0.5/care-contexts/on-discover"
    req_data = request.json
    trxn_id = req_data['transactionId']
    prev_req_id = req_data['requestId']
    req_id = str(uuid.uuid4())
    tstmp = datetime.datetime.utcnow().isoformat()[:-3]+'Z'
    payload = json.dumps({
        "requestId": req_id,
        "timestamp": tstmp,
        "transactionId": trxn_id,
        "patient": {
            "referenceNumber": "AP_Demo_4",
            "display": "Abhishek Patil",
            "careContexts": [
                {
                    "referenceNumber": "AP_D_4_CC_4",
                    "display": "AP D4CC4"
                }
            ],
            "matchedBy": [
                "MOBILE"
            ]
        },
        "resp": {
            "requestId": prev_req_id
        }
    })
    headers = {
        'Authorization': GATEWAY_AUTH_TOKEN,
        'X-CM-ID': 'sbx',
        'Content-Type': 'application/json'
    }
    on_disc_resp = requests.request("POST", cbl_url, headers=headers, data=payload)
    print(on_disc_resp)

    return jsonify(summary = {"HIP CC": "Discovery"})

#   HIP INITIATED LINKING CARE CONTEXTS URLs
@app.route('/v0.5/users/auth/on-fetch-modes', methods=['POST'])
def auth_on_fetch_modes():
    print("HIP LOG: Auth on fetch modes received!")
    print(request.json)
    return jsonify(summary = {"HIP Auth": "On Fetch Modes"})
    
@app.route('/v0.5/users/auth/on-init', methods=['POST'])
def users_auth_on_init():
    print("HIP LOG: Users auth on init received!")
    print(request.json)
    return jsonify(summary = {"HIP Users auth": "On Init"})

@app.route('/v0.5/users/auth/on-confirm', methods=['POST'])
def users_auth_on_confirm():
    print("HIP LOG: Users auth on confirm received!")
    print(request.json)
    return jsonify(summary = {"HIP Users auth": "On Confirm"})

@app.route('/v0.5/links/link/on-add-contexts', methods=['POST'])
def link_on_add_contexts():
    print("HIP LOG: Link on add contexts received!")
    print(request.json)
    return jsonify(summary = {"HIP Link": "On Add Contexts"})

@app.route('/v0.5/links/context/on-notify', methods=['POST'])
def link_on_notify():
    print("HIP LOG: Link on notify received!")
    print(request.json)
    return jsonify(summary = {"HIP Link": "On Notify"})

#   CONSENT REQUESTS URLs
@app.route('/v0.5/consents/hip/notify', methods=['POST'])
def con_hip_notify():
    print("HIP LOG: Con HIP notify received!")
    print(request.json)

    # HIP ON-NOTIFY: quickly send callback to CM about acknowledgement
    req_data = request.json
    con_art_id = req_data['notification']['consentDetail']['consentId']
    con_art_resp_req_id = req_data['requestId']
    cbl_url = f"{GATEWAY_HOST}/v0.5/consents/hip/on-notify"
    req_id = str(uuid.uuid4())
    tstmp = datetime.datetime.utcnow().isoformat()[:-3]+'Z'
    payload = json.dumps({
        "requestId": req_id,
        "timestamp": tstmp,
        "acknowledgement":{
                "status": "OK",
                "consentId": con_art_id
        },
        "error": {
            "code": 1000,
            "message": "string"
        },
        "resp": {
            "requestId": con_art_resp_req_id
        }
    })
    headers = {
        'Authorization': GATEWAY_AUTH_TOKEN,
        'X-CM-ID': 'sbx',
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", cbl_url, headers=headers, data=payload)
    print("--------- HIP LOG: HIP has sent on-notify to CM ----------")
    print(f"HIP LOG: On-notify req ID {req_id}")
    print(f"HIP LOG: On-notify timestamp {tstmp}")
    print(f"-----------------------------------")

    return jsonify(summary = {"HIP Con": "HIP Notify"})

@app.route('/v0.5/health-information/hip/request', methods=['POST'])
def hi_request():
    print("HIP LOG: HI request received!")
    print(request.json)
    return jsonify(summary = {"HIP HI": "Request"})

#   SUBSCRIPTION REQUESTS URLs
@app.route('/v0.5/subscription-requests/hiu/on-init', methods=['POST'])
def sub_req_on_init():
    print("HIP LOG: Sub Req on init received!")
    print(request.json)
    return jsonify(summary = {"HIP Sub_Req": "On Init"})

@app.route('/v0.5/subscription-requests/hiu/on-notify', methods=['POST'])
def sub_req_on_notify():
    print("HIP LOG: Sub Req on notify received!")
    print(request.json)
    return jsonify(summary = {"HIP Sub_Req": "On Notify"})

# ---------------------------- HIU ---------------------------#
#   CONSENT REQUESTS URLs
@app.route('/v0.5/patients/on-find', methods=['POST'])
def pat_on_find():
    print("HIU LOG: Patient find received!")
    print(request.json)
    return jsonify(summary = {"HIU Patient": "On Find"})

@app.route('/v0.5/consent-requests/on-init', methods=['POST'])
def con_req_on_init():
    print("HIU LOG: Con Req on init received!")
    print(request.json)
    return jsonify(summary = {"HIU Con_Req": "On Init"})

@app.route('/v0.5/consent-requests/on-status', methods=['POST'])
def con_req_on_status():
    print("HIU LOG: Con Req on status received!")
    print(request.json)
    return jsonify(summary = {"HIU Con_Req": "On Status"})

@app.route('/v0.5/consents/hiu/notify', methods=['POST'])
def con_hiu_notify():
    print("HIU LOG: Con HIU notify received!")
    print(request.json)

    # HIU ON-NOTIFY: quickly send callback to CM about acknowledgement
    req_data = request.json
    con_art_id = req_data['notification']['consentArtefacts'][0]['id']
    con_art_resp_req_id = req_data['requestId']
    cbl_url = f"{GATEWAY_HOST}/v0.5/consents/hiu/on-notify"
    req_id = str(uuid.uuid4())
    tstmp = datetime.datetime.utcnow().isoformat()[:-3]+'Z'
    payload = json.dumps({
        "requestId": req_id,
        "timestamp": tstmp,
        "acknowledgement": [
            {
                "status": "OK",
                "consentId": con_art_id
            }
        ],
        "error": {
            "code": 1000,
            "message": "string"
        },
        "resp": {
            "requestId": con_art_resp_req_id
        }
    })
    headers = {
        'Authorization': GATEWAY_AUTH_TOKEN,
        'X-CM-ID': 'sbx',
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", cbl_url, headers=headers, data=payload)
    print("--------- HIU LOG: HIU has sent on-notify to CM ----------")
    print(f"HIU LOG: On-notify req ID {req_id}")
    print(f"HIU LOG: On-notify timestamp {tstmp}")
    print(f"-----------------------------------")

    return jsonify(summary = {"HIU Con": "HIU Notify"})

@app.route('/v0.5/consents/on-fetch', methods=['POST'])
def con_on_fetch():
    print("HIU LOG: Con Art on fetch received!")
    print(request.json)
    return jsonify(summary = {"HIU Con_Art": "On Fetch"})

@app.route('/v0.5/health-information/hiu/on-request', methods=['POST'])
def hi_on_request():
    print("HIU LOG: HI on request received!")
    print(request.json)
    return jsonify(summary = {"HIU HI": "On Request"})

# --------------- DATA ENCRYPTION USING RSA ECB PCKS -------------
@app.route('/encrypt-secret/<keyType>/<secret>', methods=['POST'])
def enc_secret(keyType, secret):
    print("Encrypting secret!")
    print(keyType)
    print(type(keyType))
    print(secret)

    # url = None
    # if keyType == "0":
    #     url = "https://healthidsbx.abdm.gov.in/api/v1/auth/cert"
    # if keyType == "1":
    #     url = "https://phr.abdm.gov.in:443/api/v1/phr/public/certificate"

    # payload={}
    # headers = {
    #     'Accept-Language': 'en-US'
    # }

    # print("URL START")
    # response = requests.request("GET", url, headers=headers, data=payload)
    # print("URL END")
    # text = response.text
    # print(text)

    text = None
    if keyType == "0":
        text = """-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAstWB95C5pHLXiYW59qyO
4Xb+59KYVm9Hywbo77qETZVAyc6VIsxU+UWhd/k/YtjZibCznB+HaXWX9TVTFs9N
wgv7LRGq5uLczpZQDrU7dnGkl/urRA8p0Jv/f8T0MZdFWQgks91uFffeBmJOb58u
68ZRxSYGMPe4hb9XXKDVsgoSJaRNYviH7RgAI2QhTCwLEiMqIaUX3p1SAc178ZlN
8qHXSSGXvhDR1GKM+y2DIyJqlzfik7lD14mDY/I4lcbftib8cv7llkybtjX1Aayf
Zp4XpmIXKWv8nRM488/jOAF81Bi13paKgpjQUUuwq9tb5Qd/DChytYgBTBTJFe7i
rDFCmTIcqPr8+IMB7tXA3YXPp3z605Z6cGoYxezUm2Nz2o6oUmarDUntDhq/PnkN
ergmSeSvS8gD9DHBuJkJWZweG3xOPXiKQAUBr92mdFhJGm6fitO5jsBxgpmulxpG
0oKDy9lAOLWSqK92JMcbMNHn4wRikdI9HSiXrrI7fLhJYTbyU3I4v5ESdEsayHXu
iwO/1C8y56egzKSw44GAtEpbAkTNEEfK5H5R0QnVBIXOvfeF4tzGvmkfOO6nNXU3
o/WAdOyV3xSQ9dqLY5MEL4sJCGY1iJBIAQ452s8v0ynJG5Yq+8hNhsCVnklCzAls
IzQpnSVDUVEzv17grVAw078CAwEAAQ==
-----END PUBLIC KEY-----
"""
    if keyType == "1":
        text = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA7Zq7YKcjmccSBnR9CDHd
6IX96V7D/a2XSMs+yCgejSe956mqjA/0Q9h+Xnx7ZZdwe2Tf2Jq/mWXa+gYdnta5
8otreXg/5oGnNV3Edlixz1Oc8tJg5bG4sIUCGZcbEQGSbm1iC+Fp1kS+YLVG4Su8
KoRxcCvRJI2QkfqAruX3JoFjggOkv0TgWCo9z6NV6PPmPN3UsXyH3OPDi3Ewnvd6
4ngCUKPSBiIDwhLj2yYSShcxH8aWbrz00SJodBJzqgjvCfZuljBXXIN4Ngi/nzqE
J7woKQ1kNgWoHFZy7YL74PihW//4OlniSRoITX+7ChILIv2ezSmAdIjpNJ9Dg9XK
cQIDAQAB
-----END PUBLIC KEY-----
"""
    public_key = text.replace('\n','').split('-----')[2]
    encrypted_secret = getEncryptedText(public_key, secret)

    return jsonify({"encSecret": encrypted_secret})


if __name__ == '__main__':
    app.run(debug=True)
