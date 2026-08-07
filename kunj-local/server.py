from flask import Flask, request, jsonify, send_from_directory
import json
import os
import threading
import datetime
import random
import re

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

def now_ist():
    return datetime.datetime.now(datetime.timezone.utc).astimezone(IST)


app = Flask(__name__, static_folder='static', static_url_path='')
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.json')
lock = threading.Lock()

MONGO_URI = os.environ.get('MONGO_URI', '').strip()
_mongo_collection = None

if MONGO_URI:
    from pymongo import MongoClient
    _mongo_client = MongoClient(MONGO_URI)
    _mongo_db = _mongo_client['rox_chat']
    _mongo_collection = _mongo_db['app_data']
    print("Storage: MongoDB Atlas (persistent)")
else:
    print("Storage: local data.json (WARNING: resets on Render free-tier restarts)")


DEFAULT_ROOM = "main-room✨"
DEVICE_RETENTION_SECONDS = 24 * 60 * 60


def prune_old_devices(data):
    last_seen = data.get('device_last_seen', {})
    now = datetime.datetime.now().timestamp()
    expired = [d for d, ts in last_seen.items() if now - ts > DEVICE_RETENTION_SECONDS]
    changed = False
    if expired:
        changed = True
        for d in expired:
            last_seen.pop(d, None)
            users = data['devices'].pop(d, [])
            for u in users:
                devs = data['user_devices'].get(u)
                if devs and d in devs:
                    devs.remove(d)
                    if not devs:
                        data['user_devices'].pop(u, None)
    redirects = data.get('rename_redirects', {})
    stale_redirects = [k for k, r in redirects.items() if now - r.get('ts', 0) > 600]
    for k in stale_redirects:
        redirects.pop(k, None)
        changed = True
    return changed


def load_data():
    if _mongo_collection is not None:
        doc = _mongo_collection.find_one({'_id': 'main'})
        if not doc:
            doc = {"accounts": {}, "rooms": [], "messages": {}, "presence": {}}
        doc.pop('_id', None)
        doc.setdefault('presence', {})
    elif not os.path.exists(DATA_FILE):
        doc = {"accounts": {}, "rooms": [], "messages": {}, "presence": {}}
    else:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            doc = json.load(f)
            doc.setdefault('presence', {})
    doc.setdefault('moderation', {})
    doc.setdefault('devices', {})
    doc.setdefault('user_devices', {})
    doc.setdefault('device_last_seen', {})
    doc.setdefault('rename_redirects', {})
    needs_save = False
    if DEFAULT_ROOM not in doc['rooms']:
        doc['rooms'].insert(0, DEFAULT_ROOM)
        needs_save = True
    if prune_old_devices(doc):
        needs_save = True
    if needs_save:
        save_data(doc)
    if migrate_owner_flag(doc):
        save_data(doc)
    return doc


def migrate_owner_flag(data):
    """One-time self-heal: accounts created before the is_owner field existed
    won't have it set, even if their username is literally 'owner'. Backfill it."""
    has_flag = any(acc.get('is_owner') for acc in data['accounts'].values())
    if has_flag:
        return False
    if OWNER_USERNAME in data['accounts']:
        data['accounts'][OWNER_USERNAME]['is_owner'] = True
        return True
    return False


def save_data(data):
    if _mongo_collection is not None:
        to_save = dict(data)
        to_save['_id'] = 'main'
        _mongo_collection.replace_one({'_id': 'main'}, to_save, upsert=True)
        return
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


OWNER_USERNAME = "owner"

DEFAULT_NAME_STYLE = {"type": "plain", "color1": "", "color2": "", "font": ""}

USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_ ]+$')


def is_valid_username(name):
    return bool(name) and bool(name.strip()) and bool(USERNAME_PATTERN.match(name))

DURATION_MINUTES = {"15min": 15, "30min": 30, "2hr": 120, "24hr": 1440, "1week": 10080}


def get_owner_key(data):
    for k, acc in data['accounts'].items():
        if acc.get('is_owner'):
            return k
    if OWNER_USERNAME in data['accounts']:
        return OWNER_USERNAME
    return None


def verify_owner(data, password):
    key = get_owner_key(data)
    if not key:
        return False
    return data['accounts'][key].get('password') == password


def verify_requester_is_owner(data, requester):
    key = get_owner_key(data)
    return bool(key) and (requester or '').strip().lower() == key


def get_active_moderation(data, key, clean=True):
    entry = data['moderation'].get(key)
    if not entry:
        return None
    until = entry.get('until')
    if until is not None and datetime.datetime.now().timestamp() > until:
        if clean:
            del data['moderation'][key]
        return None
    return entry


def track_device(data, key, device_id, username_display):
    if not device_id:
        return
    data.setdefault('device_last_seen', {})[device_id] = datetime.datetime.now().timestamp()
    dev_list = data['user_devices'].setdefault(key, [])
    if device_id not in dev_list:
        dev_list.append(device_id)
    users_list = data['devices'].setdefault(device_id, [])
    if key not in users_list:
        users_list.append(key)


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/fonts', methods=['GET'])
def list_fonts():
    fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'fonts')
    allowed_ext = ('.ttf', '.otf', '.woff', '.woff2')
    result = []
    if os.path.isdir(fonts_dir):
        for filename in sorted(os.listdir(fonts_dir)):
            if filename.lower().endswith(allowed_ext):
                display = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').strip()
                result.append({"name": display, "file": filename})
    return jsonify(result)


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
    gender = (body.get('gender') or '').strip()
    age = body.get('age', '')
    device_id = (body.get('deviceId') or '').strip()
    if not username or not password:
        return jsonify({"error": "missing fields"}), 400
    if not is_valid_username(username):
        return jsonify({"error": "invalid_username"}), 400
    key = username.lower()
    with lock:
        data = load_data()
        if key in data['accounts']:
            return jsonify({"error": "taken"}), 409
        mod = get_active_moderation(data, key)
        if mod and mod['action'] in ('ban', 'kick'):
            save_data(data)
            return jsonify({"error": mod['action'], "until": mod.get('until')}), 403
        data['accounts'][key] = {
            "username": username,
            "password": password,
            "gender": gender,
            "age": age,
            "bio": "",
            "avatar": "",
            "is_owner": key == OWNER_USERNAME,
            "name_style": DEFAULT_NAME_STYLE.copy()
        }
        track_device(data, key, device_id, username)
        save_data(data)
    return jsonify({
        "ok": True, "username": username, "gender": gender, "age": age, "bio": "", "avatar": "",
        "is_owner": key == OWNER_USERNAME, "name_style": DEFAULT_NAME_STYLE.copy()
    })


@app.route('/api/login', methods=['POST'])
def login():
    body = request.get_json(force=True)
    username = (body.get('username') or '').strip()
    password = body.get('password') or ''
    device_id = (body.get('deviceId') or '').strip()
    key = username.lower()
    with lock:
        data = load_data()
    acc = data['accounts'].get(key)
    if not acc or acc['password'] != password:
        return jsonify({"error": "invalid"}), 401
    with lock:
        data = load_data()
        mod = get_active_moderation(data, key)
        if mod and mod['action'] in ('ban', 'kick'):
            save_data(data)
            return jsonify({"error": mod['action'], "until": mod.get('until')}), 403
        track_device(data, key, device_id, acc['username'])
        save_data(data)
    return jsonify({
        "ok": True,
        "username": acc['username'],
        "gender": acc.get('gender', ''),
        "age": acc.get('age', ''),
        "bio": acc.get('bio', ''),
        "avatar": acc.get('avatar', ''),
        "name_style": acc.get('name_style', DEFAULT_NAME_STYLE),
        "is_owner": key == get_owner_key(data)
    })


@app.route('/api/profile/<username>', methods=['GET'])
def get_profile(username):
    key = username.lower()
    with lock:
        data = load_data()
    acc = data['accounts'].get(key)
    if acc:
        return jsonify({
            "username": acc['username'],
            "gender": acc.get('gender', ''),
            "age": acc.get('age', ''),
            "bio": acc.get('bio', ''),
            "avatar": acc.get('avatar', ''),
            "name_style": acc.get('name_style', DEFAULT_NAME_STYLE),
            "is_owner": key == get_owner_key(data)
        })
    presence_entry = data['presence'].get(key)
    if isinstance(presence_entry, dict):
        return jsonify({
            "username": presence_entry.get('username', username),
            "gender": presence_entry.get('gender', ''),
            "age": presence_entry.get('age', ''),
            "bio": "",
            "avatar": "",
            "guest": True
        })
    return jsonify({"error": "not found"}), 404


@app.route('/api/profile', methods=['POST'])
def update_profile():
    body = request.get_json(force=True)
    username = (body.get('username') or '').strip()
    password = body.get('password') or ''
    key = username.lower()
    with lock:
        data = load_data()
        acc = data['accounts'].get(key)
        if not acc or acc['password'] != password:
            return jsonify({"error": "unauthorized"}), 401
        # username is intentionally never updated here
        if 'gender' in body:
            acc['gender'] = (body.get('gender') or '').strip()
        if 'age' in body:
            acc['age'] = body.get('age', acc.get('age', ''))
        if 'bio' in body:
            acc['bio'] = (body.get('bio') or '').strip()[:200]
        if body.get('avatar'):
            acc['avatar'] = body.get('avatar')
        if 'nameStyle' in body and isinstance(body['nameStyle'], dict):
            ns = body['nameStyle']
            acc['name_style'] = {
                "type": ns.get('type', 'plain') if ns.get('type') in ('plain', 'solid', 'gradient', 'neon') else 'plain',
                "color1": (ns.get('color1') or '')[:20],
                "color2": (ns.get('color2') or '')[:20],
                "font": (ns.get('font') or '').strip()[:120]
            }
        save_data(data)
    return jsonify({
        "ok": True,
        "username": acc['username'],
        "gender": acc.get('gender', ''),
        "age": acc.get('age', ''),
        "bio": acc.get('bio', ''),
        "avatar": acc.get('avatar', ''),
        "name_style": acc.get('name_style', DEFAULT_NAME_STYLE),
        "is_owner": key == get_owner_key(data)
    })


@app.route('/api/guest-check', methods=['POST'])
def guest_check():
    body = request.get_json(force=True)
    username = (body.get('username') or '').strip()
    device_id = (body.get('deviceId') or '').strip()
    if not username:
        return jsonify({"error": "missing username"}), 400
    if not is_valid_username(username):
        return jsonify({"error": "invalid_username"}), 400
    key = username.lower()
    with lock:
        data = load_data()
        if key in data['accounts']:
            return jsonify({"error": "taken"}), 409
        mod = get_active_moderation(data, key)
        if mod and mod['action'] in ('ban', 'kick'):
            save_data(data)
            return jsonify({"error": mod['action'], "until": mod.get('until')}), 403
        track_device(data, key, device_id, username)
        save_data(data)
    return jsonify({"ok": True})


@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    with lock:
        data = load_data()
    return jsonify(data['rooms'])


@app.route('/api/rooms', methods=['POST'])
def add_room():
    return jsonify({"error": "room creation is disabled right now"}), 403


@app.route('/api/message-count/<path:key>', methods=['GET'])
def message_count(key):
    with lock:
        data = load_data()
    return jsonify({"count": len(data['messages'].get(key, []))})


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
    now = now_ist()
    time_str = now.strftime('%H:%M')
    with lock:
        data = load_data()
        mod = get_active_moderation(data, user.lower())
        if mod:
            save_data(data)
            return jsonify({"error": mod['action'], "until": mod.get('until')}), 403
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


@app.route('/api/guest-logout', methods=['POST'])
def guest_logout():
    body = request.get_json(force=True)
    username = (body.get('username') or '').strip()
    if not username:
        return jsonify({"error": "missing username"}), 400
    key = username.lower()
    with lock:
        data = load_data()
        if key in data['accounts']:
            # registered accounts keep their history — only guests get wiped
            return jsonify({"ok": True, "skipped": "registered account"})
        keys_to_delete = [
            k for k in data['messages'].keys()
            if k.startswith('dm-msgs:') and key in k[len('dm-msgs:'):].split('__')
        ]
        for k in keys_to_delete:
            del data['messages'][k]
        # tag their past room messages so a future guest with the same
        # name isn't mistaken for them
        for k, msgs in data['messages'].items():
            if k.startswith('room-msgs:'):
                for m in msgs:
                    if m.get('user', '').lower() == key and not m['user'].startswith('#'):
                        suffix = str(random.randint(10000000, 99999999))
                        m['user'] = '#' + m['user'] + '-' + suffix
        data['presence'].pop(key, None)
        save_data(data)
    return jsonify({"ok": True, "cleared": len(keys_to_delete)})


def migrate_username(data, old_key, new_key, new_display):
    """When an account is renamed, carry all its history over to the new name."""
    if old_key == new_key:
        return

    # room messages: just relabel the sender
    for k, msgs in data['messages'].items():
        if k.startswith('room-msgs:'):
            for m in msgs:
                if m.get('user', '').lower() == old_key:
                    m['user'] = new_display

    # DM messages: the conversation key itself is built from both usernames,
    # so it has to be renamed (and merged if the new name already had one)
    for old_full_key in [k for k in data['messages'].keys() if k.startswith('dm-msgs:')]:
        pair = old_full_key[len('dm-msgs:'):]
        parts = pair.split('__')
        if old_key not in parts:
            continue
        new_parts = sorted(new_key if p == old_key else p for p in parts)
        new_full_key = 'dm-msgs:' + '__'.join(new_parts)
        msgs = data['messages'].pop(old_full_key)
        for m in msgs:
            if m.get('user', '').lower() == old_key:
                m['user'] = new_display
        existing = data['messages'].get(new_full_key, [])
        data['messages'][new_full_key] = existing + msgs

    # device tracking (multi-account detection)
    if old_key in data['user_devices']:
        devs = data['user_devices'].pop(old_key)
        merged = data['user_devices'].setdefault(new_key, [])
        for d in devs:
            if d not in merged:
                merged.append(d)
            users_list = data['devices'].setdefault(d, [])
            if old_key in users_list:
                users_list.remove(old_key)
            if new_key not in users_list:
                users_list.append(new_key)

    # any active mute/kick/ban carries over
    if old_key in data['moderation']:
        data['moderation'][new_key] = data['moderation'].pop(old_key)

    # presence (harmless if stale, but keep it tidy)
    if old_key in data['presence']:
        data['presence'][new_key] = data['presence'].pop(old_key)


@app.route('/api/owner-self-update', methods=['POST'])
def owner_self_update():
    body = request.get_json(force=True)
    current_username = (body.get('currentUsername') or '').strip()
    current_password = body.get('currentPassword') or ''
    new_username = (body.get('newUsername') or '').strip()
    new_password = body.get('newPassword') or ''
    current_key = current_username.lower()
    with lock:
        data = load_data()
        acc = data['accounts'].get(current_key)
        if not acc or acc.get('password') != current_password or not acc.get('is_owner'):
            return jsonify({"error": "unauthorized"}), 401
        if new_username and new_username.lower() != current_key:
            if not is_valid_username(new_username):
                return jsonify({"error": "invalid_username"}), 400
            new_key = new_username.lower()
            if new_key in data['accounts']:
                return jsonify({"error": "taken"}), 409
            del data['accounts'][current_key]
            acc['username'] = new_username
            acc['is_owner'] = True
            data['accounts'][new_key] = acc
            migrate_username(data, current_key, new_key, new_username)
            data['rename_redirects'][current_key] = {
                "to": new_key, "display": new_username, "ts": datetime.datetime.now().timestamp()
            }
        if new_password:
            acc['password'] = new_password
        save_data(data)
    return jsonify({"ok": True, "username": acc['username'], "is_owner": True})


@app.route('/api/owner-rename-user', methods=['POST'])
def owner_rename_user():
    body = request.get_json(force=True)
    requester = body.get('requester') or ''
    target = (body.get('target') or '').strip().lower()
    new_username = (body.get('newUsername') or '').strip()
    if not target or not new_username:
        return jsonify({"error": "missing fields"}), 400
    if not is_valid_username(new_username):
        return jsonify({"error": "invalid_username"}), 400
    new_key = new_username.lower()
    if new_key == target:
        return jsonify({"error": "same name"}), 400
    with lock:
        data = load_data()
        if not verify_requester_is_owner(data, requester):
            return jsonify({"error": "unauthorized"}), 401
        name_taken = new_key in data['accounts'] or (
            new_key in data['presence'] and new_key != target
        )
        if name_taken:
            return jsonify({"error": "taken"}), 409

        if target in data['accounts']:
            # registered account — move the whole account record
            acc = data['accounts'].pop(target)
            acc['username'] = new_username
            data['accounts'][new_key] = acc
            final_username = acc['username']
        else:
            # guest — no persistent account to move, just relabel their history
            presence_entry = data['presence'].get(target)
            final_username = new_username
            if presence_entry:
                presence_entry['username'] = new_username
                data['presence'][new_key] = data['presence'].pop(target)

        migrate_username(data, target, new_key, new_username)
        data['rename_redirects'][target] = {
            "to": new_key, "display": final_username, "ts": datetime.datetime.now().timestamp()
        }
        save_data(data)
    return jsonify({"ok": True, "username": final_username})


@app.route('/api/moderate', methods=['POST'])
def moderate():
    body = request.get_json(force=True)
    requester = body.get('requester') or ''
    target = (body.get('target') or '').strip().lower()
    action = (body.get('action') or '').strip()
    duration_key = body.get('duration', '')
    if action not in ('mute', 'kick', 'ban', 'revoke'):
        return jsonify({"error": "invalid action"}), 400
    if not target:
        return jsonify({"error": "missing target"}), 400
    with lock:
        data = load_data()
        if not verify_requester_is_owner(data, requester):
            return jsonify({"error": "unauthorized"}), 401
        if target == get_owner_key(data):
            return jsonify({"error": "cannot moderate owner"}), 403
        if action == 'revoke':
            data['moderation'].pop(target, None)
            save_data(data)
            return jsonify({"ok": True, "status": None})
        if action == 'ban':
            entry = {"action": "ban", "until": None}
        else:
            minutes = DURATION_MINUTES.get(duration_key)
            if not minutes:
                return jsonify({"error": "invalid duration"}), 400
            until = datetime.datetime.now().timestamp() + minutes * 60
            entry = {"action": action, "until": until}
        data['moderation'][target] = entry
        save_data(data)
    return jsonify({"ok": True, "status": entry})


@app.route('/api/moderation-status/<username>', methods=['GET'])
def moderation_status(username):
    key = username.lower()
    with lock:
        data = load_data()
        mod = get_active_moderation(data, key)
        save_data(data)
    if not mod:
        return jsonify({"status": None})
    remaining = None
    if mod.get('until') is not None:
        remaining = max(0, mod['until'] - datetime.datetime.now().timestamp())
    return jsonify({"status": mod['action'], "remaining": remaining})


@app.route('/api/other-accounts/<username>', methods=['GET'])
def other_accounts(username):
    requester = request.args.get('requester', '')
    key = username.lower()
    with lock:
        data = load_data()
        if not verify_requester_is_owner(data, requester):
            return jsonify({"error": "unauthorized"}), 401
        device_ids = data['user_devices'].get(key, [])
        others = set()
        for dev in device_ids:
            for u in data['devices'].get(dev, []):
                if u != key:
                    others.add(u)
    return jsonify(list(others))


@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    body = request.get_json(force=True)
    username = (body.get('username') or '').strip()
    device_id = (body.get('deviceId') or '').strip()
    if not username:
        return jsonify({"error": "missing username"}), 400
    key = username.lower()
    with lock:
        data = load_data()
        redirect = data['rename_redirects'].pop(key, None)
        if redirect:
            data['presence'].pop(key, None)
            new_key = redirect['to']
            data['presence'][new_key] = {
                "ts": datetime.datetime.now().timestamp(),
                "username": redirect['display'],
                "gender": (body.get('gender') or '').strip(),
                "age": body.get('age', '')
            }
            track_device(data, new_key, device_id, redirect['display'])
            save_data(data)
            return jsonify({"ok": True, "renamed_to": redirect['display']})
        data['presence'][key] = {
            "ts": datetime.datetime.now().timestamp(),
            "username": username,
            "gender": (body.get('gender') or '').strip(),
            "age": body.get('age', '')
        }
        track_device(data, key, device_id, username)
        save_data(data)
    return jsonify({"ok": True})


@app.route('/api/online', methods=['GET'])
def online_users():
    with lock:
        data = load_data()
    now = datetime.datetime.now().timestamp()
    online = []
    for u, entry in data['presence'].items():
        ts = entry.get('ts') if isinstance(entry, dict) else entry
        if ts and now - ts < 10:
            online.append(u)
    return jsonify(online)


ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Kunj Admin</title>
<style>
  body{background:#101F1A;color:#F5F1E8;font-family:sans-serif;padding:24px;max-width:820px;margin:0 auto;}
  h2{font-family:serif;}
  input{background:#1E362A;border:1px solid #333;color:#fff;padding:8px 10px;border-radius:6px;width:280px;}
  textarea{width:100%;height:420px;background:#1E362A;color:#F5F1E8;border:1px solid #333;border-radius:8px;padding:12px;font-family:monospace;font-size:13px;box-sizing:border-box;}
  button{background:#EC5A82;border:none;color:#fff;padding:9px 18px;border-radius:8px;font-weight:bold;cursor:pointer;margin-left:8px;}
  #status{margin:10px 0;font-size:14px;}
</style>
</head>
<body>
  <h2>Kunj — data.json editor</h2>
  <p>Apni ADMIN_KEY daalo aur Load dabao. Edit karke Save dabao.</p>
  <input id="key" placeholder="ADMIN_KEY" type="password">
  <button onclick="loadData()">Load</button>
  <button onclick="saveData()">Save</button>
  <div id="status"></div>
  <textarea id="editor" placeholder="Data yaha dikhega Load karne ke baad..."></textarea>

<script>
async function loadData(){
  const key = document.getElementById('key').value;
  const status = document.getElementById('status');
  status.textContent = 'Loading...';
  try{
    const res = await fetch('/api/dump?key=' + encodeURIComponent(key));
    if(!res.ok){ status.textContent = 'Galat key ya error.'; return; }
    const data = await res.json();
    document.getElementById('editor').value = JSON.stringify(data, null, 2);
    status.textContent = 'Loaded. Ab edit karke Save dabao.';
  }catch(e){ status.textContent = 'Error: ' + e; }
}

async function saveData(){
  const key = document.getElementById('key').value;
  const status = document.getElementById('status');
  let parsed;
  try{
    parsed = JSON.parse(document.getElementById('editor').value);
  }catch(e){
    status.textContent = 'JSON galat hai, check kar comma/bracket. Error: ' + e.message;
    return;
  }
  status.textContent = 'Saving...';
  try{
    const res = await fetch('/api/dump?key=' + encodeURIComponent(key), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(parsed)
    });
    if(!res.ok){ status.textContent = 'Save fail hua. Galat key?'; return; }
    status.textContent = 'Saved! ✅';
  }catch(e){ status.textContent = 'Error: ' + e; }
}
</script>
</body>
</html>
"""


@app.route('/admin')
def admin_page():
    return ADMIN_HTML


@app.route('/api/dump', methods=['GET', 'POST'])
def dump_data():
    key = request.args.get('key', '')
    expected = os.environ.get('ADMIN_KEY', 'changeme123')
    if key != expected:
        return jsonify({"error": "unauthorized"}), 401
    if request.method == 'POST':
        try:
            new_data = request.get_json(force=True)
        except Exception:
            return jsonify({"error": "invalid json"}), 400
        if not isinstance(new_data, dict) or not all(
            k in new_data for k in ("accounts", "rooms", "messages")
        ):
            return jsonify({"error": "missing required keys (accounts, rooms, messages)"}), 400
        new_data.setdefault("presence", {})
        with lock:
            save_data(new_data)
        return jsonify({"ok": True})
    with lock:
        data = load_data()
    return jsonify(data)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("")
    print("Kunj chat server chal raha hai.")
    print("Isi PC par kholo:  http://localhost:" + str(port))
    print("Doosre devices ke liye apna local IP nikaalo (ipconfig) aur us IP:" + str(port) + " par kholo.")
    print("")
    app.run(host='0.0.0.0', port=port, debug=False)
