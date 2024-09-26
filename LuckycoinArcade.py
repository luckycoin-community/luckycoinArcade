from flask import Flask, abort, render_template, render_template_string, send_file, request, jsonify
import os
from threading import Lock, local
from concurrent.futures import ThreadPoolExecutor
import re
import queue
from getOrdContent import process_tx
from bitcoinrpc.authproxy import JSONRPCException
import configparser
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import sys
import socket
import time
import requests

app = Flask(__name__)

# Queue to manage tasks
task_queue = queue.Queue()
# Thread pool to handle concurrent processing
thread_pool = ThreadPoolExecutor(max_workers=4)
# Thread-local storage for RPC connections
thread_local = local()

# Shared flag and lock to indicate processing state
processing_flag = False
processing_lock = Lock()

def get_rpc_connection():
    if not hasattr(thread_local, "rpc_connection"):
        from getOrdContent import rpc_connection
        thread_local.rpc_connection = rpc_connection
    return thread_local.rpc_connection

def is_hexadecimal(s):
    """Check if the string s is a valid hexadecimal string."""
    return re.fullmatch(r'^[0-9a-fA-F]+$', s) is not None

def process_task(genesis_txid, depth=1000):
    global processing_flag
    with processing_lock:
        processing_flag = True
    try:
        print(f"Starting processing for {genesis_txid}")
        process_tx(genesis_txid, depth)
    except JSONRPCException as e:
        print(f"JSONRPCException: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        with processing_lock:
            processing_flag = False
        print(f"Finished processing for {genesis_txid}")
        task_queue.task_done()

@app.route('/')
def landing_page():
    return render_template('landing_page.html')

@app.route('/content/<file_id>i0')
def serve_content(file_id):
    global processing_flag
    with processing_lock:
        if processing_flag:
            return jsonify({"message": "Server is busy processing ordinal. Please try again later."}), 503

    filename = f"{file_id}"
    content_dir = './content'
    file_path = next((os.path.join(content_dir, file) for file in os.listdir(content_dir) if file.startswith(filename)), None)
    
    if file_path and os.path.isfile(file_path):
        print(f"File found: {file_path}")

        if file_path.endswith('.html'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                return render_template_string(html_content)
            except Exception as e:
                print(f"Error reading HTML file: {e}")
                abort(500)
        elif file_path.endswith('.webp'):
            return send_file(file_path, mimetype='image/webp')
        else:
            return send_file(file_path)
    else:
        print(f"File not found: {filename} in {content_dir}")
        abort(404)

@app.errorhandler(404)
def not_found_error(error):
    global processing_flag
    request_path = request.path.split('/')[-1]
    genesis_txid = request_path[:-2] if request_path.endswith('i0') else None

    if not genesis_txid or not is_hexadecimal(genesis_txid):
        print(f"Invalid genesis_txid: {request_path}")
        return "Invalid transaction ID", 400

    with processing_lock:
        if not processing_flag:
            thread_pool.submit(process_task, genesis_txid, 1000)

    return "Processing ordinal, click refresh when complete", 404

@app.route('/favicon.ico')
def favicon():
    return send_file('favicon.ico', mimetype='image/x-icon')

# Load RPC credentials from rpc.conf
config = configparser.ConfigParser()
config.read('rpc.conf')

RPC_USER = config.get('rpc', 'user')
RPC_PASSWORD = config.get('rpc', 'password')
RPC_HOST = config.get('rpc', 'host')
RPC_PORT = config.getint('rpc', 'port')

# Construct the RPC URL
RPC_URL = f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}"

print(f"Attempting to connect to {RPC_HOST}:{RPC_PORT}")

# Test network connectivity
try:
    socket.create_connection((RPC_HOST, RPC_PORT), timeout=10)
    print(f"Network connection to {RPC_HOST}:{RPC_PORT} successful")
except socket.error as e:
    print(f"Network error: {e}")
    sys.exit(1)

# Function to test RPC connection
def test_rpc_connection(retries=3, delay=5):
    for attempt in range(retries):
        try:
            # Try a simple RPC call
            response = requests.post(RPC_URL, 
                json={"method": "getblockcount", "params": [], "id": 1},
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    print(f"RPC connection successful. Block count: {result['result']}")
                    return True
                else:
                    print(f"Unexpected RPC response: {result}")
            else:
                print(f"RPC request failed with status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"RPC connection attempt {attempt + 1} failed: {e}")
        
        if attempt < retries - 1:
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)
    
    return False

# Test RPC connection
if not test_rpc_connection():
    print("Failed to establish RPC connection after multiple attempts.")
    sys.exit(1)

# If we get here, RPC connection was successful
print("RPC connection established successfully.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

