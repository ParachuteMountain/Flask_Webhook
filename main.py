from flask import Flask, request, Response, render_template, jsonify

from fidelius_enc_dec import *

from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_v1_5
import requests
import uuid
import datetime
import json
import base64
import subprocess
import os
import stat

app = Flask(__name__)

# HOME PAGE / FIST PAGE
@app.route('/')
def home():
    return jsonify(summary = {"Home": "Home v9"})

# ABDM BASE URLs
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

# ---------------------------- HIP ---------------------------#
# PATIENT's PROFILE SHARE
@app.route('/v1.0/patients/profile/share', methods=['POST'])
def pat_prof_share():
    print("HIP LOG: Patient profile shared and received!")
    print(request.json)

    # callback to acknowledge successfull profile share    
    cbl_url = f"{GATEWAY_HOST}/v1.0/patients/profile/on-share"
    req_data = request.json
    prev_req_id = req_data['requestId']
    req_intent = req_data['intent']
    req_location = req_data['location']
    req_profile_hipCode = req_data['profile']['hipCode']
    req_profile_patient = req_data['profile']['patient']
    print(req_profile_patient)
    req_id = str(uuid.uuid4())
    tstmp = datetime.datetime.utcnow().isoformat()[:-3]+'Z'
    # Sample error code if failed
    # "error": {
    #     "code": 1000,
    #     "message": "string"
    # },
    payload = json.dumps({
        "requestId": req_id,
        "timestamp": tstmp,
        "acknowledgement": {
            "status": "SUCCESS",
            "healthId": req_profile_patient['healthId'],
            "tokenNumber": "1234567"
        },
        "resp": {
            "requestId": prev_req_id
        }
    })
    headers = {
        'Authorization': GATEWAY_AUTH_TOKEN,
        'X-CM-ID': 'sbx'
    }
    on_share_resp = requests.request("POST", cbl_url, headers=headers, data=payload)
    print(on_share_resp)

    # now use the req_profile_patient values like HID number and Demographics to verify
    # FIRST, save the health ID and patient demographics as usual in DB

    # Then somewhere outside if we know we are doing this for verification (KYC) then we do 
    # auth init with Demograhics:
    #     auth/fetch-modes -> auth/init -> auth/confirm -> link/add-contexts -> context/notify
    # This is in Postman M1_Wise_APIs and will be called by the mobile app
    # We will need to tell the app (or the HIP hospital application) to start the 
    #     verification process and also pass the demographics info from here
    # FILL THAT CODE HERE - an API call to the app


    return jsonify(summary = {"HIP Patient": "Prof Share"})

# PATIENT STATUS NOTIFY
@app.route('/v0.5/patients/status/notify', methods=['POST'])
def pat_status_notify():
    print("HIP LOG: Patient status notify received!")
    print(request.json)

    # When we receive this we save a patient's status in the DB
    # If active we can do other APIs else we report it as Deactivated / Deleted.

    # callback to acknowledge successfull status receiving
    cbl_url = f"{GATEWAY_HOST}/v0.5/patients/status/on-notify"
    req_data = request.json
    prev_req_id = req_data['requestId']
    req_id = str(uuid.uuid4())
    tstmp = datetime.datetime.utcnow().isoformat()[:-3]+'Z'
    # Sample error code if failed
    # "error": {
    #     "code": 1000,
    #     "message": "string"
    # },
    payload = json.dumps({
        "requestId": req_id,
        "timestamp": tstmp,
        "acknowledgment": {
            "status": "OK"
        },
        "resp": {
            "requestId": prev_req_id
        }
    })
    headers = {
        'Authorization': GATEWAY_AUTH_TOKEN,
        'X-CM-ID': 'sbx'
    }
    on_notif_status_resp = requests.request("POST", cbl_url, headers=headers, data=payload)
    print(on_notif_status_resp)

    return jsonify(summary = {"HIP Patient": "Status notify"})

#   PATIENT INITIATED LINKING
@app.route('/v0.5/care-contexts/discover', methods=['POST'])
def pat_init_cc_link_disc():
    print("HIP LOG: Care contexts discovery received!")
    req_data = request.json
    print(req_data)

    # first do some searching in the HRP itself based on request.json data information
    # req_data Example: {'patient': {'id': 'm1test.1092@sbx', 'name': 'Abhishek Suhasrao Patil', 'gender': 'M', 'yearOfBirth': 1996, 'verifiedIdentifiers': [{'type': 'MOBILE', 'value': '8976165694'}, {'type': 'NDHM_HEALTH_NUMBER', 'value': '91-3108-7321-4236'}, {'type': 'HEALTH_ID', 'value': 'm1test.1092@sbx'}], 'unverifiedIdentifiers': [{'type': 'MOBILE', 'value': '+917499094276'}]}, 'requestId': '8d795bc1-b464-4cb1-98f2-c1adab2631c2', 'timestamp': '2022-11-01T11:11:44.115743', 'transactionId': '245a7942-ba04-4dbf-85a5-96d718c88d37'}
    # IMPORTANT: SAVE the ABHA ID for this patient in DB too!
    # Get the care contexts for the patient using Fuzzy Match
    # Check for more info: F:\AbPt_ABDM\FHIR\FHIR_Understanding\CC+FHIR\HIP_CC file
    # =================== YOU MUST GIVE MASKED DETAILS FOR CARE CONTEXTS ================
    # Give patient info if found (even with 0 CC) - MUST GIVE ALL RECORDS OVER THE YEARS!
    # else add the usual 'error' key-value pair (check sandbox of this URL as example)

    # we must reply with on-discover as an HIP
    cbl_url = f"{GATEWAY_HOST}/v0.5/care-contexts/on-discover"
    trxn_id = req_data['transactionId']
    prev_req_id = req_data['requestId']
    req_id = str(uuid.uuid4())
    tstmp = datetime.datetime.utcnow().isoformat()[:-3]+'Z'
    payload = json.dumps({
        "requestId": req_id,
        "timestamp": tstmp,
        "transactionId": trxn_id,
        "patient": {
            "referenceNumber": "FL_Demo_1",
            "display": "Firsttest Lasttest",
            "careContexts": [],
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
        'X-CM-ID': 'sbx'
    }
    on_disc_resp = requests.request("POST", cbl_url, headers=headers, data=payload)
    # gives no content 202 response
    print(on_disc_resp)

    # 2 MORE THINGS TO DO:
    #   1. Save transactionId and remember who did it and it was for discovery
    #   2. Also, send OTP to patient and save and confirm that ourselves

    return jsonify(summary = {"HIP CC": "Discovery"})

@app.route('/v0.5/links/link/init', methods=['POST'])
def pat_init_cc_link_init():
    print("HIP LOG: Patient initiated links init received!")
    print(request.json)

    # we must reply with on-init as an HIP
    cbl_url = f"{GATEWAY_HOST}/v0.5/links/link/on-init"
    req_data = request.json
    # req_data Example: {'requestId': '5066c19b-4ef2-4f13-8c6f-dede5d35ef25', 'timestamp': '2022-11-01T11:13:34.453199', 'transactionId': '245a7942-ba04-4dbf-85a5-96d718c88d37', 'patient': {'id': 'm1test.1092@sbx', 'referenceNumber': 'AP_Demo_1', 'careContexts': [{'referenceNumber': 'PAT_AP_D1CC1'}]}}
    trxn_id = req_data['transactionId']

    # 2 THINGS TO DO:
    #   1. CONFIRM THIS trxn_id matches transactionId saved in discovery
    #   2. Also, confirm OTP sent is properly entered by patient
    #       - Send token as a success to the OTP validation
    #   3. Then confirm that the incoming care context is one of the values provided in discovery
    # ONLY THEN MOVE FORWARD

    # Give patient info if found (even with 0 CC) 
    # else add the usual 'error' key-value pair (check sandbox of this URL as example)

    # both the details of patient and the CCs to add should be remembered for on-confirm in the next step
    pat_dets = req_data['patient']
    cc_to_add_dets_list = pat_dets['careContexts']
    prev_req_id = req_data['requestId']
    req_id = str(uuid.uuid4())
    tstmp = datetime.datetime.utcnow().isoformat()[:-3]+'Z'
    comm_exp_nonutc = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    comm_exp = comm_exp_nonutc.isoformat()[:-3]+'Z'
    payload = json.dumps({
        "requestId": req_id,
        "timestamp": tstmp,
        "transactionId": trxn_id,
        "link": {
            "referenceNumber": "PAT_INIT_LINK_10_OCT_2022",
            "authenticationType": "DIRECT",
            "meta": {
                "communicationMedium": "MOBILE",
                "communicationHint": "OTP on Reg. Mob. XXXXXXXX76", # can also add patient health ID to be more exact
                "communicationExpiry": comm_exp
            }
        },
        "resp": {
            "requestId": prev_req_id
        }
    })
    headers = {
        'Authorization': GATEWAY_AUTH_TOKEN,
        'X-CM-ID': 'sbx'
    }
    on_init_resp = requests.request("POST", cbl_url, headers=headers, data=payload)
    # gives no content 202 response
    print(on_init_resp)

    return jsonify(summary = {"HIP CC": "Links Init"})

@app.route('/v0.5/links/link/confirm', methods=['POST'])
def pat_init_cc_link_confirm():
    print("HIP LOG: Patient initiated links confirm received!")
    print(request.json)

    # we must reply with on-confirm as an HIP
    cbl_url = f"{GATEWAY_HOST}/v0.5/links/link/on-confirm"
    req_data = request.json
    # req_data Example: {'requestId': 'fe9cd614-e630-4ce1-9abe-cb690db19e08', 'timestamp': '2022-11-01T11:14:54.294276', 'confirmation': {'linkRefNumber': 'PAT_INIT_LINK_10_OCT_2022', 'token': 'test_token'}}
    prev_req_id = req_data['requestId']
    conf_link_ref_num = req_data['confirmation']['linkRefNumber']
    conf_token = req_data['confirmation']['token']

    # Once we get link ref num and token in request.json we do the following:
    # 1. The link reference number
    #   - must be same for this patient - as given in on-init URL call (previous step)
    # 2. The token
    #   - must be same one as sent
    #   - must be from same CM
    # 3. Results of unmasked linked care contexts with patient reference number
    # Recheck the sandbox of this URL for additional understanding if needed

    # There is a case where a user is never found.
    # Then, create a reference ID and name for them and pass it below to start linking.
    # Also in this case keep care contexts list empty.

    req_id = str(uuid.uuid4())
    tstmp = datetime.datetime.utcnow().isoformat()[:-3]+'Z'
    payload = json.dumps({
        "requestId": req_id,
        "timestamp": tstmp,
        "patient": {
            "referenceNumber": "FL_Demo_1",
            "display": "Firsttest Lasttest",
            "careContexts": [
                {
                    "referenceNumber": "PAT_FL_D1CC1",
                    "display": "Patient Init D1 CC1"    # this display might not come from patient so will need to fill with meaningful text
                }
            ]
        },
        "resp": {
            "requestId": prev_req_id
        }
    })
    headers = {
        'Authorization': GATEWAY_AUTH_TOKEN,
        'X-CM-ID': 'sbx'
    }
    on_conf_resp = requests.request("POST", cbl_url, headers=headers, data=payload)
    # gives no content 202 response
    print(on_conf_resp)

    return jsonify(summary = {"HIP CC": "Links Confirm"})

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

@app.route('/v0.5/users/auth/notify', methods=['POST'])
def users_auth_notify():
    # use ONLY when doing Direct mode of authentication
    # When Auth Init uses Direct mode and confirms it 
    # in the users/auth/confirm and on-confirm section then users/auth/notify gets called
    # Lets us know the auth is done - to which we reply using on-notify as an ACK

    print("HIP LOG: Auth notify for Direct auth received!")
    print(request.json)

    # send on-notify to Gateway
    cbl_url = f"{GATEWAY_HOST}/v0.5/users/auth/on-notify"
    req_data = request.json
    # req_data Example: no example as no direct mode available for authentication in my example
    prev_req_id = req_data['requestId']
    req_id = str(uuid.uuid4())
    tstmp = datetime.datetime.utcnow().isoformat()[:-3]+'Z'
    payload = json.dumps({
        "requestId": req_id,
        "timestamp": tstmp,
        "acknowledgement": {
            "status": "OK"
        },
        "resp": {
            "requestId": prev_req_id
        }
    })
    headers = {
        'Authorization': GATEWAY_AUTH_TOKEN,
        'X-CM-ID': 'sbx'
    }
    on_notif_resp = requests.request("POST", cbl_url, headers=headers, data=payload)
    print(on_notif_resp)

    return jsonify(summary = {"HIP Notify": "For direct auth"})

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

# LISTEN TO REPLY FOR ANY NOTIFICATION (including new data notif) FROM HIP
@app.route('/v0.5/patients/sms/on-notify', methods=['POST'])
def pat_sms_on_notify():
    print("HIP LOG: Patients SMS no notify!")
    print(request.json)
    return jsonify(summary = {"HIP Pat SMS": "On Notify"})

#   CONSENT REQUESTS URLs
@app.route('/v0.5/consents/hip/notify', methods=['POST'])
def con_hip_notify():
    print("HIP LOG: Con HIP notify received!")
    print(request.json)

    # We can get GRANTED, REVOKED and even EXPIRED values
    # FIRST, save the consent against ABHA Address for GRANTED
    #    or delete existing ones for REVOKED/EXPIRED values
    # THEN, send acknowledgement callback below

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
    print(response)
    print(f"HIP LOG: On-notify req ID {req_id}")
    print(f"HIP LOG: On-notify timestamp {tstmp}")
    print(f"-----------------------------------")

    return jsonify(summary = {"HIP Con": "HIP Notify"})

@app.route('/v0.5/health-information/hip/request', methods=['POST'])
def hi_request():
    print("HIP LOG: HI request received!")
    print(request.json)

    # Capture information for bundle transfer
    req_data = request.json
    hi_req_trxnId = req_data['transactionId']  #### USE THIS IN DATA TRANSFER
    hi_req_info = req_data['hiRequest']
    hi_req_consent = hi_req_info['consent']
    hi_req_dataRange = hi_req_info['dateRange']
    hi_req_dataPushUrl = hi_req_info['dataPushUrl']
    hi_req_keyMaterial = hi_req_info['keyMaterial']

    # Step 1: Ensure all information is upto standards and send ACK using hip/on-request
    cbl_url = f"{hi_req_dataPushUrl}/v0.5/health-information/hip/on-request"
    prev_req_id = req_data['requestId']
    req_id = str(uuid.uuid4())
    tstmp = datetime.datetime.utcnow().isoformat()[:-3]+'Z'
    payload = json.dumps({
        "requestId": req_id,
        "timestamp": tstmp,
        "hiRequest": {
            "transactionId": hi_req_trxnId,
            "sessionStatus": "ACKNOWLEDGED"
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
    response = requests.request("POST", cbl_url, headers=headers, data=payload)
    print(response)

    # Step 2: Then prepare FHIR data, do enc and send accordingly - FOR EACH CONSENT ARTFACT
    # # Open JSON FHIR file path and read data from it
    # f = open("OPCnsltNoteSmpl.json")
    # data = json.load(f)
    # f.close()
    # strData = json.dumps(data)
    # # create dictionary to pass outside pub key and nonce
    # outsidePubKeyMaterial = {
    #     'nonce': hi_req_keyMaterial['nonce'],
    #     'publicKey': hi_req_keyMaterial['dhPublicKey']['keyValue']
    # }
    # ret_val = runExample1(strData, outsidePubKeyMaterial)
    # enc_content = ret_val['content']
    # enc_snd_pub_key = ret_val['senderPubKeyVal']
    # enc_snd_nonce = ret_val['senderNonceVal']

    # # Preparing reply data
    # cbl_url = f"{hi_req_dataPushUrl}/v0.5/health-information/transfer"
    # dh_pub_key_exp = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    # dh_pub_key_exp = dh_pub_key_exp.isoformat()[:-3]+'Z'
    # payload = json.dumps({
    #     "pageNumber": 1,
    #     "pageCount": 1,
    #     "transactionId": hi_req_trxnId,
    #     "entries": [
    #         {
    #             "content": enc_content,
    #             "media": "application/fhir+json",
    #             "checksum": "string",
    #             "careContextReference": "AP_D1_CC1"
    #         }
    #     ],
    #     "keyMaterial": {
    #         "cryptoAlg": "ECDH",
    #         "curve": "Curve25519",
    #         "dhPublicKey": {
    #             "expiry": dh_pub_key_exp,
    #             "parameters": "Curve25519/32byte random key",
    #             "keyValue": enc_snd_pub_key
    #         },
    #         "nonce": enc_snd_nonce
    #     }
    # })
    # headers = {
    #     'Authorization': GATEWAY_AUTH_TOKEN,
    #     'Content-Type': 'application/json'
    # }
    # response = requests.request("POST", cbl_url, headers=headers, data=payload)
    # print(response)

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
    print(response)
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
