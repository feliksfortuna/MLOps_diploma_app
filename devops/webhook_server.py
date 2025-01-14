# webhook_server.py
from flask import Flask
import subprocess

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    # Trigger the webhook_listener.sh script
    subprocess.Popen(['./webhook_listener.sh'])
    return 'Webhook received', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)