from flask import Flask, request, jsonify, send_from_directory
import json
import os
import threading
import datetime

app = Flask(__name__, static_folder='static', static_url_path='')
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.json')
lock = threading.Lock()


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"accounts": {}, "rooms": [], "messages": {}, "presence": {}}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        data.setdefault('presence', {})
        return data


def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    with lock:
        data = load_data()
    return jsonify(data['accounts'])


@app.route('/api/signup', methods=['POST'])
def signup():
    body = request.get_json(force=True)
    username = (body.get('username') or '').strip()
    password = body.get('password') or ''
    if not username or not password:
        return jsonify({"error": "missing fields"}), 400
    key = username.lower()
    with lock:
        data = load_data()
        if key in data['accounts']:
            return jsonify({"error": "taken"}), 409
        data['accounts'][key] = {"username": username, "password": password}
        save_data(data)
    return jsonify({"ok": True, "username": username})


@app.route('/api/login', methods=['POST'])
def login():
    body = request.get_json(force=True)
    username = (body.get('username') or '').strip()
    password = body.get('password') or ''
    key = username.lower()
    with lock:
        data = load_data()
    acc = data['accounts'].get(key)
    if not acc or acc['password'] != password:
        return jsonify({"error": "invalid"}), 401
    return jsonify({"ok": True, "username": acc['username']})


@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    with lock:
        data = load_data()
    return jsonify(data['rooms'])


@app.route('/api/rooms', methods=['POST'])
def add_room():
    body = request.get_json(force=True)
    name = (body.get('name') or '').strip().lower().replace(' ', '-')
    if not name:
        return jsonify({"error": "missing name"}), 400
    with lock:
        data = load_data()
        if name not in data['rooms']:
            data['rooms'].append(name)
            save_data(data)
    return jsonify({"ok": True})


@app.route('/api/messages/<path:key>', methods=['GET'])
def get_messages(key):
    with lock:
        data = load_data()
    return jsonify(data['messages'].get(key, []))


@app.route('/api/messages/<path:key>', methods=['POST'])
def post_message(key):
    body = request.get_json(force=True)
    user = (body.get('user') or '').strip()
    text = (body.get('text') or '').strip()
    if not user or not text:
        return jsonify({"error": "missing"}), 400
    now = datetime.datetime.now()
    time_str = now.strftime('%H:%M')
    with lock:
        data = load_data()
        msgs = data['messages'].setdefault(key, [])
        msgs.append({"user": user, "text": text, "time": time_str})
        if len(msgs) > 300:
            msgs = msgs[-300:]
        data['messages'][key] = msgs
        save_data(data)
    return jsonify({"ok": True})


@app.route('/api/dm-contacts/<username>', methods=['GET'])
def dm_contacts(username):
    key = username.lower()
    with lock:
        data = load_data()
    contacts = set()
    for k in data['messages'].keys():
        if k.startswith('dm-msgs:'):
            pair = k[len('dm-msgs:'):]
            parts = pair.split('__')
            if key in parts:
                other = [p for p in parts if p != key]
                if other:
                    contacts.add(other[0])
    return jsonify(list(contacts))


@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    body = request.get_json(force=True)
    username = (body.get('username') or '').strip()
    if not username:
        return jsonify({"error": "missing username"}), 400
    with lock:
        data = load_data()
        data['presence'][username.lower()] = datetime.datetime.now().timestamp()
        save_data(data)
    return jsonify({"ok": True})


@app.route('/api/online', methods=['GET'])
def online_users():
    with lock:
        data = load_data()
    now = datetime.datetime.now().timestamp()
    online = [u for u, ts in data['presence'].items() if now - ts < 10]
    return jsonify(online)


if __name__ == '__main__':
    print("")
    print("Kunj chat server chal raha hai.")
    print("Isi PC par kholo:  http://localhost:5000")
    print("Doosre devices ke liye apna local IP nikaalo (ipconfig) aur us IP:5000 par kholo.")
    print("")
    app.run(host='0.0.0.0', port=5000, debug=False)
