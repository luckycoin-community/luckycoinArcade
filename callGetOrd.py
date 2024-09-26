from getOrdContent import process_tx

def main():
    # Placeholder for the genesis_txid
    genesis_txid = "056f4472aa241072f0bc3e5928ef5e52fe657918c94edff6c7aa96760c130422"
    
    # Call the process_tx function with the genesis_txid and a depth of 500
    process_tx(genesis_txid, depth=1000)

if __name__ == "__main__":
    main()
