import json
import datetime
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import configparser
import os

# Function to derive Dogecoin addresses and private keys from a seed phrase
def derive_dogecoin_addresses(seed_phrase, max_consecutive_unused=20):
    # Generate seed from the mnemonic phrase
    seed_bytes = Bip39SeedGenerator(seed_phrase).Generate()

    # Create a BIP44 wallet for Dogecoin
    bip44_mst = Bip44.FromSeed(seed_bytes, Bip44Coins.DOGECOIN)

    addresses_and_keys = []
    unused_addresses_count = 0
    i = 0

    # Connect to Dogecoin Core RPC
    rpc_connection = connect_to_rpc()

    # Continue deriving addresses until a certain number of consecutive unused addresses is reached
    while unused_addresses_count < max_consecutive_unused:
        bip44_acc = bip44_mst.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i)
        address = bip44_acc.PublicKey().ToAddress()
        private_key = bip44_acc.PrivateKey().ToWif()

        try:
            # Check if the address has been used
            balance = rpc_connection.getreceivedbyaddress(address)
            if balance == 0:
                unused_addresses_count += 1
            else:
                unused_addresses_count = 0
        except JSONRPCException:
            unused_addresses_count += 1

        # Add the address and key to the list
        addresses_and_keys.append({
            "address": address,
            "private_key": private_key
        })

        # Move to the next address
        i += 1

    return addresses_and_keys

# Function to save the addresses and keys to a new JSON file
def save_to_json(data):
    # Create a unique filename with a timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'dogecoin_addresses_{timestamp}.json'

    # Determine the main directory and create the misc directory if it doesn't exist
    main_directory = os.path.dirname(os.path.abspath(__file__))
    misc_directory = os.path.join(main_directory, 'misc')
    os.makedirs(misc_directory, exist_ok=True)

    # Save the file in the misc directory
    file_path = os.path.join(misc_directory, filename)
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)
    print(f"Addresses and keys have been saved to {file_path}")

# Function to interact with Dogecoin Core RPC
def connect_to_rpc():
    # Read the rpc.conf file from the main directory
    config = configparser.ConfigParser()
    config.read('rpc.conf')

    rpc_user = config['rpc']['user']
    rpc_password = config['rpc']['password']
    rpc_host = config['rpc'].get('host', '127.0.0.1')
    rpc_port = config['rpc'].get('port', '22555')

    rpc_url = f"http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}"
    return AuthServiceProxy(rpc_url)

# Main function
def main():
    # Prompt the user to enter their seed phrase
    seed_phrase = input("Enter your Dogecoin seed phrase: ")

    # Derive Dogecoin addresses and private keys
    addresses_and_keys = derive_dogecoin_addresses(seed_phrase)

    # Save the derived addresses and private keys to a new JSON file
    save_to_json(addresses_and_keys)

if __name__ == "__main__":
    main()

