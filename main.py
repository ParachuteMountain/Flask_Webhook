from flask import Flask, request, Response, render_template, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify(summary = {"Home": "Home v2"})

@app.route('/v0.5/patients/on-find', methods=['POST'])
def pat_on_find():
    print("Patient find received!")
    print(request.json)
    return jsonify(summary = {"Patient": "On Find"})

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

if __name__ == '__main__':
    app.run(debug=False)
