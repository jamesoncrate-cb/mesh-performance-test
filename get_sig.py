import os
from dotenv import load_dotenv
from eth_account import Account

# load_dotenv('examples/ethereum/.env')
load_dotenv(".env")
private_key = os.environ["PREFUNDED_PRIVATE_KEY"]
# tx_hash = '0x799181b88e8db932901e2bdb6074e45e8b718ea509399998635dd2bb7dc959f2'
tx_hash = "0x06d71b7c166932004433b4b6c7c5dfdddbd06531f3f744e5db6475c76a7289b8"
signed_message = Account.unsafe_sign_hash(tx_hash, private_key=private_key)
print(signed_message)

derived_address = Account.from_key(private_key).address
print(derived_address)
