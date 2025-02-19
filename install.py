import subprocess
import time
import secrets
import base64
import os
import sys
import math
import json
from datetime import datetime, timedelta

IOCLINK_VERSION = "1.0.1"


# Handle different Python versions for UTC
try:
    from datetime import UTC
    def get_utc_now():
        return datetime.now(UTC)
except ImportError:
    def get_utc_now():
        return datetime.utcnow()



def check_dependencies():
    """Check if required dependencies are installed"""
    print("Checking dependencies...")
    
    if not check_docker():
        print("❌ Docker is not installed. Please install Docker and try again.")
        sys.exit(1)
    print("✅ Docker is installed")

    if not check_docker_compose():
        print("❌ Docker Compose is not installed. Please install Docker Compose and try again.")
        sys.exit(1)
    print("✅ Docker Compose is installed\n")

def check_docker():
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_docker_compose():
    try:
        subprocess.run(["docker-compose", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_installation_directory():
    while True:
        print("\nEnter the path you would like your iOCLink configuration files and logs to be saved to.")
        dir_to_use = input("\nPath: ").strip()
        if not dir_to_use:
            print("Directory path cannot be empty.")
            continue
        
        if not os.path.exists(dir_to_use):
            create = input(f"Directory {dir_to_use} does not exist. Create it? (y/n): ").lower()
            if create == 'y':
                try:
                    os.makedirs(dir_to_use)
                    print(f"✅ Created directory: {os.path.abspath(dir_to_use)}")
                    return dir_to_use
                except Exception as e:
                    print(f"❌ Error creating directory: {e}")
                    continue
        else:
            print(f"✅ Using existing directory: {os.path.abspath(dir_to_use)}")
            return dir_to_use

def get_port():
    while True:
        try:
            print("\nEnter the port you would like the Web Console to run on (1024-65535). Please ensure this port is not already in use.")
            port = input("Port: ").strip()
            port_num = int(port)
            if 1024 <= port_num <= 65535:
                return port
            print("Please enter a port number between 1024 and 65535")
        except ValueError:
            print("Please enter a valid port number")

def validate_timezone(tz):
    if not tz or '/' not in tz:
        return False
    parts = tz.split('/')
    if len(parts) != 2:
        return False
    if not all(part[0].isupper() for part in parts):
        return False
    return True

def get_timezone():
    print("\nEnter timezone (e.g., Australia/Melbourne)")
    while True:
        timezone = input("Timezone: ").strip()
        if validate_timezone(timezone):
            return timezone
        print("Invalid timezone format! Please use format 'Region/City' (e.g., Australia/Melbourne)")

def generate_config_data():
    current_time = get_utc_now()
    hours_from_now = current_time + timedelta(hours=2)
    run_at_hour = math.ceil(hours_from_now.hour)
    run_at_time = f"{run_at_hour:02d}:00"
    week_ago = current_time - timedelta(weeks=1)
    last_run_time = f"{week_ago.strftime('%Y-%m-%d')} {run_at_time}:00"
    yesterday = current_time - timedelta(days=1)
    last_scheduled_run = f"{yesterday.strftime('%Y-%m-%d')} {run_at_time}:00"

    return {
        "version": IOCLINK_VERSION,
        "s1_api_key": "",
        "s1_id": "",
        "s1_id_type": "account_id",
        "s1_url": "",
        "misp_api_key": "",
        "misp_url": "",
        "max_api_attempts": 5,
        "disabled_feeds": [],
        "last_run_time": last_run_time,
        "last_scheduled_run": last_scheduled_run,
        "scheduled_run_interval": 1,
        "run_at_time": run_at_time,
        "stats": {
            "iocs_sent": 0,
            "iocs_sent_trend": [0],
            "s1_calls": 0,
            "s1_calls_trend": [0],
            "run_time": 0.0,
            "run_time_trend": [0.0],
            "sha_1_sent": 0,
            "sha_256_sent": 0,
            "md5_sent": 0,
            "ip_sent": 0,
            "url_sent": 0,
            "domain_sent": 0
        }
    }



def main():
    print("\n=== IOCLink Setup Script ===")
    print(f"Version: {IOCLINK_VERSION}\n")
    check_dependencies()
    

    install_dir = get_installation_directory()
    port = get_port()
    timezone = get_timezone()
    

    print("\nGenerating security keys...")
    secret_key = secrets.token_hex(32)
    aes_key = base64.b64encode(os.urandom(32)).decode('utf-8')
    rabbitmq_user = secrets.token_hex(8)  
    rabbitmq_pass = secrets.token_hex(16) 
    

    path_join = os.path.join(install_dir, 'iocLink')
    os.makedirs(path_join + '/configs', exist_ok=True)
    os.makedirs(path_join + '/logs', exist_ok=True)
    

    env_content = f"""WEBUI_USER=ChangeMe
WEBUI_PASS=ChangeMe

SECRET_KEY={secret_key}
AES_KEY={aes_key}
TIMEZONE={timezone}
WEBUI_PORT={port}
APP_DATA_PATH={path_join}/
RABBITMQ_DEFAULT_USER={rabbitmq_user}
RABBITMQ_DEFAULT_PASS={rabbitmq_pass}
"""
    with open('.env', 'w') as f:
        f.write(env_content)
    print("✅ Generated .env file")
    
    # Generate and write config file
    config_path = f"{path_join}/configs/configs.json"
    if os.path.exists(config_path):
        if input("\nconfigs.json already exists at your desired path. Overwrite? (y/n): ").lower() != 'y':
            print("Setup aborted. Please backup existing configs.json and try again.")
            sys.exit(1)
    
    try:
        with open(config_path, 'w') as f:
            json.dump(generate_config_data(), f, indent=4)
        print("✅ Generated configs.json")
    except Exception as e:
        print(f"❌ Error writing configs.json: {e}")
        sys.exit(1)
    
    print("\n=== Setup Complete! ===")
    print("\n The iOCLink Worker has been scheduled to run in two hours time. This can be changed in the Web Management Console.")
    print("\n Note: The Web Management Console credentials are set to: ChangeMe, ChangeMe. Please update the following variables in the .env file:")
    print("   - WEBUI_USER")
    print("   - WEBUI_PASS")
    print("\n➡️  Next steps:")
    print(f"   1. Ensure port {port} is open in your firewall")
    print("   2. Run 'docker-compose up -d' to start the Worker and Management Console")


if __name__ == "__main__":
    main()
