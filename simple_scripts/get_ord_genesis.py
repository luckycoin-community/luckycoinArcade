from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from decimal import Decimal

# Configuration
RPC_USER = "your_rpc_user"
RPC_PASSWORD = "your_rpc_password"
RPC_HOST = "127.0.0.1"
RPC_PORT = 19918

# Connect to the Dogecoin node
rpc_connection = AuthServiceProxy(f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}")

# Initial Transaction ID and specific output index to inspect
txid = "763d4b4b23c096209ce70d1b620bd773ac6492a7ae2fc5a5e1f2e77417293d08"
output_index = 1

def get_previous_tx_output(txid, vout):
    try:
        prev_tx = rpc_connection.getrawtransaction(txid, True)
        return prev_tx['vout'][vout]
    except JSONRPCException as e:
        print(f"An error occurred: {e}")
        return None

def get_sigscript_asm(txid, vout):
    try:
        prev_tx = rpc_connection.getrawtransaction(txid, True)
        return prev_tx['vin'][vout]['scriptSig']['asm']
    except IndexError:
        print("not an ord")
        return None
    except JSONRPCException as e:
        print(f"An error occurred while fetching sigscript asm: {e}")
        return None

def process_transaction(txid, output_index):
    try:
        transaction = rpc_connection.getrawtransaction(txid, True)
    except JSONRPCException as e:
        print(f"An error occurred: {e}")
        return None, None

    vins = transaction['vin']
    vouts = transaction['vout']

    vin_values = []
    vin_details = []
    for vin in vins:
        prev_tx_output = get_previous_tx_output(vin['txid'], vin['vout'])
        if prev_tx_output:
            vin_values.append(prev_tx_output['value'])
            vin_details.append((vin['txid'], vin['vout']))
        else:
            vin_values.append(Decimal('0'))
            vin_details.append((vin['txid'], vin['vout']))

    vin_remaining_values = vin_values[:]

    chosen_vout_info = None
    for vout_index, vout in enumerate(vouts):
        remaining_value = vout['value']
        corresponding_vins = []
        
        for vin_index, vin_value in enumerate(vin_remaining_values):
            if remaining_value > 0 and vin_remaining_values[vin_index] > 0:
                if vin_remaining_values[vin_index] >= remaining_value:
                    vin_remaining_values[vin_index] -= remaining_value
                    corresponding_vins.append(vin_index)
                    remaining_value = 0
                else:
                    remaining_value -= vin_remaining_values[vin_index]
                    corresponding_vins.append(vin_index)
                    vin_remaining_values[vin_index] = 0

        if vout_index == output_index:
            chosen_vout_info = {
                "vout_index": vout_index,
                "value": vout['value'],
                "corresponding_vins": corresponding_vins
            }

    if chosen_vout_info and chosen_vout_info['corresponding_vins']:
        for vin_index in chosen_vout_info['corresponding_vins']:
            vin_txid, vout_idx = vin_details[vin_index]
            sigscript_asm = get_sigscript_asm(vin_txid, vout_idx)
            if sigscript_asm is None:
                return None, None
            if sigscript_asm.split()[0] == "6582895":
                ord_genesis = vin_txid
                print(f"Stopping loop as sigscript asm index 0 equals 6582895")
                print(f"ord_genesis: {ord_genesis}")
                return None, None
            print(f"Previous TXID: {vin_txid}, VOUT Index: {vout_idx}, SigScript ASM: {sigscript_asm}")
            return vin_txid, vout_idx
    else:
        return None, None

# Loop until an error occurs or the condition is met
current_txid = txid
current_output_index = output_index

while current_txid is not None and current_output_index is not None:
    current_txid, current_output_index = process_transaction(current_txid, current_output_index)
