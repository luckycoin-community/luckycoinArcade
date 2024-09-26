from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from decimal import Decimal
import base64

# Configuration
RPC_USER = "your_rpc_user"
RPC_PASSWORD = "your_rpc_password"
RPC_HOST = "127.0.0.1"
RPC_PORT = 8332

# Connect to the bellscoin node
rpc_connection = AuthServiceProxy(f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}")

# Transaction ID
txid = "e0689b6dcf006acf0aa008160bae0a14fd31f5cc672853ae1f8f7ddc5f947761"

ORDINAL_SIGNIFIER = "6582895"

def decode_script(script_hex):
    try:
        decoded_script = rpc_connection.decodescript(script_hex)
        return decoded_script.get("asm", "N/A")
    except JSONRPCException as e:
        print(f"An error occurred: {e}")
        return "N/A"

def hex_to_base64(hex_string):
    return base64.b64encode(bytes.fromhex(hex_string)).decode('utf-8')

def extract_ordinal_data(asm):
    parts = asm.split()
    if len(parts) < 8 or parts[4] != ORDINAL_SIGNIFIER:
        return None, None

    mime_type = bytes.fromhex(parts[6]).decode('utf-8')
    data = parts[8]

    return mime_type, data

def print_transaction_data(txid):
    try:
        transaction = rpc_connection.getrawtransaction(txid, True)

        for vin_index, vin in enumerate(transaction['vin']):
            print(f"\nInput {vin_index}:")
            if 'txinwitness' in vin:
                print("Witness data:")
                for witness_index, witness_item in enumerate(vin['txinwitness']):
                    print(f"  Witness {witness_index}: {witness_item}")
                    asm = decode_script(witness_item)
                    print(f"  Decoded ASM: {asm}")
                    mime_type, data = extract_ordinal_data(asm)
                    if mime_type and data:
                        print(f"  MIME Type: {mime_type}")
                        print(f"  Ordinal Data (Base64): {hex_to_base64(data)}")
            else:
                print("  No witness data for this input")

        if all('txinwitness' not in vin for vin in transaction['vin']):
            print("\nNo witness data found in this transaction.")

    except JSONRPCException as e:
        print(f"An error occurred: {e}")

# Print the transaction data to the console
print_transaction_data(txid)
