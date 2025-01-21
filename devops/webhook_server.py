# webhook_server.py
from flask import Flask
from flask_cors import CORS
import subprocess

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost", "http://seito.lavbic.net", "https://ultimate-krill-officially.ngrok-free.app"]}})

@app.route('/webhook', methods=['POST'])
def webhook():
    # Trigger the webhook_listener.sh script
    subprocess.Popen(['./webhook_listener.sh'])
    return 'Webhook received', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)