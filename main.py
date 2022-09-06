from flask import Flask, request, Response, render_template, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify(summary = {"HOME": "Home v2"})

@app.route('/v0.5/patients/on-find', methods=['POST'])
def pat_on_find():
    print("Patient find received!")
    # print(request.json)
    return render_template("index.html")
    return jsonify(summary = {"Patient Find Response": request.json})

@app.route('/v0.5/consent-requests/on-init', methods=['POST'])
def con_req_on_init():
    print("Con Req on init received!")
    # print(request.json)
    return jsonify(summary = {"Con Req on init Response": request.json})

if __name__ == '__main__':
    app.run(debug=False)
