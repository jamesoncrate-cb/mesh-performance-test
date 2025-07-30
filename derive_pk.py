# Derive public key from private key
try:
    # Convert hex private key to bytes
    private_key_bytes = binascii.unhexlify(PRIVATE_KEY)

    private_key_hex = os.environ["PREFUNDED_PRIVATE_KEY"]
    private_key_bytes = hexadecimal.decode_hex(private_key_hex)
    private_key = keys.PrivateKey(private_key_bytes)
    public_key = private_key.public_key
    public_key_hex = "0x04" + public_key.to_hex()

    print(f"Derived public key: {PUBLIC_KEY}")

except Exception as e:
    print(f"Error deriving public key: {e}")
    sys.exit(1)
