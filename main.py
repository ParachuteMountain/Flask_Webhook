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

# HOME PAGE / FIRST PAGE
@app.route('/')
def home():
    return jsonify(summary = {"Home": "Home v10"})

# ABDM BASE URLs
MAIN_URL = "https://dev.abdm.gov.in"
GATEWAY_HOST = f"{MAIN_URL}/gateway"
CM_URL = f"{MAIN_URL}/cm"

#______________________________________BOTH HIP/HIU-START______________________________________#
# PATIENT STATUS NOTIFY
@app.route('/v0.5/patients/status/notify', methods=['POST'])
def pat_status_notify():
    print("HIP/HIU LOG: Patient status notify received!")
    print(request.json)

    # When we receive this we save a patient's status in the DB
    # If active we can process other ABDM APIs else we report it as Deactivated / Deleted.

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

    return jsonify(summary = {"HIP/HIU Patient": "Status notify"})
#_______________________________________BOTH HIP/HIU END_______________________________________#

#___________________________________________HIU-START__________________________________________#
#   SUBSCRIPTION REQUESTS URLs
@app.route('/v0.5/subscription-requests/hiu/on-init', methods=['POST'])
def sub_req_on_init():
    print("HIU LOG: Sub Req on init received!")
    print(request.json)

    # get the subscription ID and save it to the DB along with the ID of to-be-subscribed patient
    req_data = request.json
    prev_req_id = req_data['requestId']
    req_sub_req_id = req_data["subscriptionRequest"]["id"]

    return jsonify(summary = {"HIU Sub_Req": "On Init"})

# get notified for an Accepte/Denied sub request - patient Accepts/Denies in PHR app
@app.route('/v0.5/subscription-requests/hiu/notify', methods=['POST'])
def sub_req_notify():
    print("HIU LOG: Sub Req notification received!")
    print(request.json)

    # get the following information from data received
    req_data = request.json
    # - sub request ID
    req_sub_notif = req_data['notification']
    req_sub_req_id = req_sub_notif['subscriptionRequestId']
    # - grant status
    req_grant_status = req_sub_notif['status']
    # - subscription details
    req_sub_details = req_sub_notif['subscription']
    #   - sub ID
    req_sub_id = req_sub_details['id']
    #   - link/data sources - list of sources (dicts) each dict having 
    #       - 'hip' info dict ('id' and 'name' keys)
    #       - 'categories' - list with 'LINK'/'DATA'/both
    #       - 'period' dict ('from' and 'to' keys)
    req_sub_srcs = req_sub_details['sources']
    # FIND OR STORE all this for a specific patient PHR ID - sub req ID - sub ID - sub details stuff
    # Note: this can come in multiple times for same sub req ID 
    # - Have a flag of Granted/Denied for each subscription
    # - change this flag everytime we come here and the sub gets active/denied

    # callback with ACK of the request recieved    
    cbl_url = f"{GATEWAY_HOST}/v0.5/subscription-requests/hiu/on-notify"
    prev_req_id = req_data['requestId']
    req_id = str(uuid.uuid4())
    tstmp = datetime.datetime.utcnow().isoformat()[:-3]+'Z'
    # Sample error    
    # "error": {
    #     "code": 1000,
    #     "message": "string"
    # },
    payload = json.dumps({
        "requestId": req_id,
        "timestamp": tstmp,
        "acknowledgement": {
            "status": "OK",
            "subscriptionRequestId": req_sub_req_id
        },
        "resp": {
            "requestId": prev_req_id
        }
    })
    headers = {
        'Authorization': GATEWAY_AUTH_TOKEN,
        'X-CM-ID': 'sbx'
    }
    on_notif_sub_req_resp = requests.request("POST", cbl_url, headers=headers, data=payload)
    print(on_notif_sub_req_resp)

    return jsonify(summary = {"HIU Sub_Req": "Notification + ACK ON-NOTIFY"})

@app.route('/v0.5/subscriptions/hiu/notify', methods=['POST'])
def sub_notif():
    print("HIU LOG: New data generated notification received!")
    print(request.json)

    # if event.category = LINK, 
    #   then only CCs are passed when new CCs are linked to patients. hiTypes comes empty list.
    # If event.category = DATA,
    #   then hiTypes are passed - hiTypes is filled. 
    #   CC is passed only if the subscribed HIU has any valid consent for that CC
    
    # get the following information from data received
    req_data = request.json
    # - event info
    req_event = req_data['event']
    req_event_id = req_event['id']
    req_event_pub = req_event['published']
    req_event_sub_id = req_event['subscriptionId'] # not same as subcription ID
    req_event_cat = req_event['category'] # LINK or DATA
    # - content in the event
    req_event_content = req_event['content']
    # Example content data
    # "content": {
    #   "patient": {
    #     "id": "hinapatel@ndhm"
    #   },
    #   "hip": {
    #     "id": "string"
    #   },
    #   "context": [
    #     {
    #       "careContext": {
    #         "patientReference": "batman@tmh",
    #         "careContextReference": "Episode1"
    #       },
    #       "hiTypes": [
    #         "OPConsultation"
    #       ]
    #     }
    #   ]
    # }
    # Note: here we can save the pat ref, CC ref, HI types for particular patient
    #  - ONLY SAVE UNTIL SUB LASTS

    # callback with ACK of the request recieved
    prev_req_id = req_data['requestId']
    cbl_url = f"{GATEWAY_HOST}/v0.5/subscriptions/hiu/on-notify"
    req_id = str(uuid.uuid4())
    tstmp = datetime.datetime.utcnow().isoformat()[:-3]+'Z'
    # Sample error    
    # "error": {
    #     "code": 1000,
    #     "message": "string"
    # },
    payload = json.dumps({
        "requestId": req_id,
        "timestamp": tstmp,
        "acknowledgement": {
            "status": "OK",
            "eventId": req_event_sub_id
        },
        "resp": {
            "requestId": prev_req_id
        }
    })
    headers = {
        'Authorization': GATEWAY_AUTH_TOKEN,
        'X-CM-ID': 'sbx'
    }
    sub_notify_resp = requests.request("POST", cbl_url, headers=headers, data=payload)
    print(sub_notify_resp)

    return jsonify(summary = {"HIU Sub": "New link/data notification + ACK ON-NOTIFY"})

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
#___________________________________________HIU - END__________________________________________#

#___________________________________________HIP-START__________________________________________#
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
    # This is received when patient logs into PHR App and has HIP and CCs connected to it
    # - For each CC a GRANTED notify is received with purpose of SELF_REQUESTED
    # - ALso store the date range and allowed HI Types - ONLY THESE INFO should be shared


    # Regardless of where the notify comes from we do following:-
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
    #### USE FOLLOWING IN DATA TRANSFER
    hi_req_trxnId = req_data['transactionId']
    hi_req_info = req_data['hiRequest']
    hi_req_consent = hi_req_info['consent']
    hi_req_dataRange = hi_req_info['dateRange']
    hi_req_dataPushUrl = hi_req_info['dataPushUrl']
    hi_req_keyMaterial = hi_req_info['keyMaterial']

    # PRE-STEP ensure the consent ID here has a GRANT and signature in the DB
    # this GRANT comes in consents/hip/notify and it should be put to DB there

    # Step 1 - ON-REQUEST: Ensure all information is upto standards and send ACK using hip/on-request
    cbl_url = f"{GATEWAY_HOST}/v0.5/health-information/hip/on-request"
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
    # reget auth token to run APIs after it
    get_gateway_token()

    response = requests.request("POST", cbl_url, headers=headers, data=payload)
    print(f"Response for {hi_req_trxnId} is:----")
    print(response)

    # Step 2 - FHIR DATA TRANSFER: Then prepare FHIR data, do enc and send accordingly
    # - DO THIS FOR EACH CONSENT ARTFACT
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
    #     "pageNumber": 0,
    #     "pageCount": 0,
    #     "transactionId": hi_req_trxnId,
    #     "entries": [
    #         {
    #             "content": "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",
    #             "media": "application/fhir+json",
    #             "checksum": "string",
    #             "careContextReference": "AP_D1_CC1"
    #         }
    #     ],
    #     "keyMaterial": {
    #         "cryptoAlg": "ECDH",
    #         "curve": "Curve25519",
    #         "dhPublicKey": {
    #             "expiry": "{{HIP_PUBKEY_TIME_END}}",
    #             "parameters": "Curve25519/32byte random key",
    #             "keyValue": "BB2PH5aBbEsjs73JhI6VAA+RiJGTWQYUo9lyqd79FhJaLX4LYz6I6xwNDpy61VVG8BLzSJH8ex9tByKGECIs570="
    #         },
    #         "nonce": "daVqlvQgkMMpC0s7aVphfORAfRD5VGZYwVBPD//Pd8o="
    #     }
    # })
    # headers = {
    #     'Authorization': GATEWAY_AUTH_TOKEN,
    #     'Content-Type': 'application/json'
    # }
    # transf_resp = requests.request("POST", cbl_url, headers=headers, data=payload)
    # print(transf_resp)

    # # Step 3 - NOTIFY: notify the gateway that the transfer is successfully done from our side
    # cbl_url = f"{GATEWAY_HOST}/v0.5/health-information/notify"
    # req_id = str(uuid.uuid4())
    # tstmp = datetime.datetime.utcnow().isoformat()[:-3]+'Z'
    # payload = json.dumps({
    #     "requestId": req_id,
    #     "timestamp": tstmp,
    #     "notification": {
    #         "consentId": "<consent artefact ID>",
    #         "transactionId": "<corresponding transaction ID>",
    #         "doneAt": "<save the timestamp at which transfer was done>",
    #         "notifier": {
    #             "type": "HIP",
    #             "id": "HIPTst1"
    #         },
    #         "statusNotification": {
    #             "sessionStatus": "TRANSFERRED",  # one of [TRANSFERRED, FAILED]
    #             "hipId": "HIPTst1",
    #             "statusResponses": [ # give status for each CC
    #                 {
    #                     "careContextReference": "<CC Ref Number>",
    #                     "hiStatus": "DELIVERED", #  one of [ DELIVERED, ERRORED ]
    #                     "description": "<any string>"
    #                 }
    #             ]
    #         }
    #     }
    # })
    # headers = {
    #     'Authorization': GATEWAY_AUTH_TOKEN,
    #     'X-CM-ID': 'sbx',
    #     'Content-Type': 'application/json'
    # }
    # hi_notify_resp = requests.request("POST", cbl_url, headers=headers, data=payload)
    # print("--------- HIP LOG: HIP has sent Health Info Notify to CM ----------")
    # print(hi_notify_resp)

    return jsonify(summary = {"HIP HI": "Request + On-Request + Data Transfer + Notify"})
#___________________________________________HIP - END__________________________________________#

#__________________________________________MISC - START________________________________________#
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

# --------------- DATA ENCRYPTION USING RSA ECB PCKS -------------    
# Function encrypting secret using RSA PCKS
def getEncryptedText(rsaKey, secret):
    keyDER = base64.b64decode(rsaKey)
    keyPub = RSA.importKey(keyDER)
    cipherRSA = PKCS1_v1_5.new(keyPub)
    ciphertext = cipherRSA.encrypt(str.encode(secret))
    emsg = base64.b64encode(ciphertext)
    return emsg.decode()

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
#___________________________________________MISC-END__________________________________________#

if __name__ == '__main__':
    app.run(debug=True)
