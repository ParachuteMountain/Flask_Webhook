from flask import Flask, request, Response

app = Flask(__name__)

@app.route('/')
def home():
    return {"home":"home"}

@app.route('/v0.5/consent-requests/on-init/', methods=['POST'])
def respond():
    print("On_Init Recived!")
    print(request.json)
    return Response(status=200)

if __name__ == '__main__':
    app.run(debug=False)
