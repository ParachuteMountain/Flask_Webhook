from flask import Flask, request, Response

app = Flask(__name__)

@app.route('/')
def home():
    return {"home":"home"}

@app.route('/webhook/v0.5/consent-requests/on-init', methods=['POST'])
def respond():
    print(request.json);
    return Response(status=200)

if __name__ == '__main__':
    app.run(debug=False)
