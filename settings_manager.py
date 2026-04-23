import json
import os
import sys

# Determine path for persistent settings
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SETTINGS_FILE = os.path.join(BASE_DIR, 'user_profiles.json')

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading settings: {e}")
        return {}

def save_settings(data):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")

def get_profile_settings(profile_name):
    data = load_settings()
    return data.get(profile_name, {})

def update_profile_section(profile_name, section, config):
    data = load_settings()
    if profile_name not in data:
        data[profile_name] = {}
    data[profile_name][section] = config
    save_settings(data)
