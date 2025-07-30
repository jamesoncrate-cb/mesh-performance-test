#!/usr/bin/env python3
"""
Construction API test script for Ethereum Sepolia
Sends various construction API requests to a local Rosetta node

Usage:
    python construction.py derive                              # Test single endpoint
    python construction.py all                                 # Test all endpoints
    python construction.py -h                                  # Show help
    python construction.py --base-url http://node:8080 derive # Custom base URL
    python construction.py --env-file .env derive             # Custom env file

Requirements:
    pip install requests python-dotenv ecdsa
"""

import binascii
import requests
import json
import argparse
import sys
import os
import codecs
import ecdsa
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import sha3
from eth_keys import keys
from eth_utils import hexadecimal


# Base URL for local Rosetta node
BASE_URL = "http://localhost:8080"

# Network identifier for Ethereum Sepolia
NETWORK_IDENTIFIER = {"blockchain": "worldchain", "network": "sepolia"}

# ETH currency
ETH_CURRENCY = {"symbol": "ETH", "decimals": 18}

# Global variables that will be set from environment
FROM_ADDRESS = None
TO_ADDRESS = None
PUBLIC_KEY = None
PRIVATE_KEY = None
# EXAMPLE_UNSIGNED_TX = "{\"from\":\"0xCD0e5427035F757aC2cE8804152e160607a277Ff\",\"to\":\"0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed\",\"value\":\"50\",\"nonce\":0,\"gas_price\":\"20000000000\",\"gas_limit\":21000,\"chain_id\":11155111}"
# EXAMPLE_SIGNED_TX = "{\"signed_transaction\":\"0xf868808504a817c800825208945aaeb6053f3e94c9b9a09f33669435e7ef1beaed32808401546d71a00f09b11aeb64dc91fdcc0adff499069804a81943c708b022ad1e4ff321636513a07b9ca57b587cb1b9f06e2427726d5924b8c9f2222c08dc2b3b9b540cda281ea3\",\"currency\":{\"decimals\":18,\"symbol\":\"ETH\"}}"
# EXAMPLE_SIGNED_HASH = "0x0f09b11aeb64dc91fdcc0adff499069804a81943c708b022ad1e4ff3216365137b9ca57b587cb1b9f06e2427726d5924b8c9f2222c08dc2b3b9b540cda281ea31b"
EXAMPLE_UNSIGNED_TX = '{"from":"0xCD0e5427035F757aC2cE8804152e160607a277Ff","to":"0x786896Bb6f6ff73c9fBa9651d20a4a536ECD0BeF","value":"50","nonce":0,"gas_price":"20000000000","gas_limit":21000,"chain_id":4801}'
EXAMPLE_SIGNED_TX = '{"signed_transaction":"0xf866808504a817c80082520894786896bb6f6ff73c9fba9651d20a4a536ecd0bef32808225a5a0d7f56921caad50cdd568f17df2f5916ebeaf78502fb864faf7225bb0649e7ac6a051671ac937e4337761bf5a69b926c227c16f81acdb8183407fc88e19c57334e9","currency":{"decimals":18,"symbol":"ETH"}}'
EXAMPLE_SIGNED_HASH = "0xd7f56921caad50cdd568f17df2f5916ebeaf78502fb864faf7225bb0649e7ac651671ac937e4337761bf5a69b926c227c16f81acdb8183407fc88e19c57334e91b"


def load_environment(env_file: Optional[str] = None):
    """Load environment variables and derive public key from private key"""
    global FROM_ADDRESS, TO_ADDRESS, PUBLIC_KEY, PRIVATE_KEY

    # Load environment file
    if env_file:
        if not os.path.exists(env_file):
            print(f"Error: Environment file '{env_file}' not found")
            sys.exit(1)
        load_dotenv(env_file)
    else:
        # Try to load from default locations
        env_paths = [".env", "examples/ethereum/.env", "../.env"]
        for path in env_paths:
            if os.path.exists(path):
                print(f"Loading environment from: {path}")
                load_dotenv(path)
                break

    # Get private key from environment
    PRIVATE_KEY = os.getenv("PREFUNDED_PRIVATE_KEY")
    if not PRIVATE_KEY:
        print("Error: PREFUNDED_PRIVATE_KEY not found in environment")
        print("Please set it in your .env file or as an environment variable")
        sys.exit(1)

    # Remove 0x prefix if present
    if PRIVATE_KEY.startswith("0x"):
        PRIVATE_KEY = PRIVATE_KEY[2:]

    # Get address from environment
    FROM_ADDRESS = os.getenv("PREFUNDED_ADDRESS")
    if not FROM_ADDRESS:
        print("Error: PREFUNDED_ADDRESS not found in environment")
        sys.exit(1)

    PUBLIC_KEY = os.getenv("PREFUNDED_PUBLIC_KEY")

    # Set default TO_ADDRESS if not provided
    if not TO_ADDRESS:
        # TO_ADDRESS = "5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"  # Example address
        TO_ADDRESS = "786896Bb6f6ff73c9fBa9651d20a4a536ECD0BeF"  # Example address


def pretty_print_response(endpoint: str, response: requests.Response) -> None:
    """Pretty print API response"""
    print(f"\n{'=' * 60}")
    print(f"Endpoint: {endpoint}")
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
    print(f"{'=' * 60}\n")


def send_request(endpoint: str, data: Dict[str, Any]) -> requests.Response:
    """Send POST request to endpoint"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=data)
    pretty_print_response(endpoint, response)
    return response


def test_derive():
    """Test /construction/derive endpoint"""
    print("\n1. Testing /construction/derive")
    data = {
        "network_identifier": NETWORK_IDENTIFIER,
        "public_key": {"hex_bytes": PUBLIC_KEY, "curve_type": "secp256k1"},
        "metadata": {},
    }
    return send_request("/construction/derive", data)


def test_preprocess(amount: str = "1000000000000000000"):
    """Test /construction/preprocess endpoint"""
    print("\n2. Testing /construction/preprocess")

    # Example transfer operation
    operations = [
        {
            "operation_identifier": {"index": 0},
            "type": "CALL",
            "account": {"address": FROM_ADDRESS},
            "amount": {
                "value": f"-{amount}",  # Negative amount for sender
                "currency": ETH_CURRENCY,
            },
        },
        {
            "operation_identifier": {"index": 1},
            "related_operations": [{"index": 0}],
            "type": "CALL",
            "account": {"address": TO_ADDRESS},
            "amount": {
                "value": amount,  # Positive amount for receiver
                "currency": ETH_CURRENCY,
            },
        },
    ]

    data = {
        "network_identifier": NETWORK_IDENTIFIER,
        "operations": operations,
        "metadata": {"gas_limit": "21000", "gas_price": "20000000000"},  # 20 gwei
    }
    return send_request("/construction/preprocess", data)


def test_metadata(
    options: Optional[Dict[str, Any]] = None, amount: str = "100000000000000000"
):
    """Test /construction/metadata endpoint"""
    print("\n3. Testing /construction/metadata")

    data = {
        "network_identifier": NETWORK_IDENTIFIER,
        "options": options or {"from": FROM_ADDRESS, "to": TO_ADDRESS, "value": amount},
    }
    return send_request("/construction/metadata", data)


def test_payloads(amount: str = "1000000000000000000"):
    """Test /construction/payloads endpoint"""
    print("\n4. Testing /construction/payloads")

    operations = [
        {
            "operation_identifier": {"index": 0},
            "type": "CALL",
            "account": {"address": FROM_ADDRESS},
            "amount": {"value": f"-{amount}", "currency": ETH_CURRENCY},
        },
        {
            "operation_identifier": {"index": 1},
            "related_operations": [{"index": 0}],
            "type": "CALL",
            "account": {"address": TO_ADDRESS},
            "amount": {"value": amount, "currency": ETH_CURRENCY},
        },
    ]

    data = {
        "network_identifier": NETWORK_IDENTIFIER,
        "operations": operations,
        "metadata": {
            "nonce": 0,
            "gas_price": "20000000000",
            "gas_limit": 21000,
            "chain_id": 11155111,  # Sepolia chain ID
        },
        "public_keys": [{"hex_bytes": PUBLIC_KEY, "curve_type": "secp256k1"}],
    }
    return send_request("/construction/payloads", data)


def test_parse(transaction: str, signed: bool = False):
    """Test /construction/parse endpoint"""
    parse_type = "signed" if signed else "unsigned"
    print(f"\n5. Testing /construction/parse ({parse_type})")

    data = {
        "network_identifier": NETWORK_IDENTIFIER,
        "signed": signed,
        "transaction": transaction,
    }
    return send_request("/construction/parse", data)


def test_combine(unsigned_transaction: str, signed_hash: str):
    """Test /construction/combine endpoint"""
    print("\n6. Testing /construction/combine")

    data = {
        "network_identifier": NETWORK_IDENTIFIER,
        "unsigned_transaction": unsigned_transaction,
        "signatures": [
            {
                "signing_payload": {
                    "hex_bytes": signed_hash,
                    "account_identifier": {
                        "address": FROM_ADDRESS,
                    },
                    "signature_type": "ecdsa_recovery",
                },
                "public_key": {"hex_bytes": PUBLIC_KEY, "curve_type": "secp256k1"},
                "signature_type": "ecdsa_recovery",
                "hex_bytes": signed_hash,
            }
        ],
    }
    return send_request("/construction/combine", data)


def test_hash(signed_transaction: str):
    """Test /construction/hash endpoint"""
    print("\n7. Testing /construction/hash")

    data = {
        "network_identifier": NETWORK_IDENTIFIER,
        "signed_transaction": signed_transaction,
    }
    return send_request("/construction/hash", data)


def test_submit(signed_transaction: str):
    """Test /construction/submit endpoint"""
    print("\n8. Testing /construction/submit")

    data = {
        "network_identifier": NETWORK_IDENTIFIER,
        "signed_transaction": signed_transaction,
    }
    return send_request("/construction/submit", data)


def create_parser():
    """Create command-line argument parser"""
    parser = argparse.ArgumentParser(
        description="Construction API test script for Ethereum Sepolia",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s derive              # Test /construction/derive endpoint
  %(prog)s preprocess          # Test /construction/preprocess endpoint
  %(prog)s all                 # Test all endpoints
  %(prog)s --base-url http://example.com:8080 derive  # Use custom base URL
  %(prog)s --env-file custom.env derive               # Use custom env file
        """,
    )

    parser.add_argument(
        "endpoint",
        choices=[
            "derive",
            "preprocess",
            "metadata",
            "payloads",
            "parse",
            "combine",
            "hash",
            "submit",
            "all",
        ],
        help="The endpoint to test or 'all' to test all endpoints",
    )

    parser.add_argument(
        "--base-url",
        default="http://localhost:8080",
        help="Base URL for Rosetta node (default: %(default)s)",
    )

    parser.add_argument(
        "--env-file", help="Path to environment file (default: auto-detect .env)"
    )

    parser.add_argument(
        "--to-address",
        help="To address for transaction operations (default: example address)",
    )

    parser.add_argument(
        "--amount",
        default="50",
        help="Amount in wei to transfer (default: %(default)s - 1 ETH)",
    )

    return parser


def main():
    """Run construction API tests based on command-line arguments"""
    parser = create_parser()
    args = parser.parse_args()

    # Load environment variables and derive keys
    load_environment(args.env_file)

    # Update global variables
    global BASE_URL, TO_ADDRESS
    BASE_URL = args.base_url

    if args.to_address:
        TO_ADDRESS = args.to_address

    print("Starting Construction API tests for Ethereum Sepolia")
    print(f"Base URL: {BASE_URL}")
    print(f"From Address: {FROM_ADDRESS}")
    print(f"To Address: {TO_ADDRESS}")
    print(f"Amount: {args.amount} wei")
    print("-" * 60)

    try:
        if args.endpoint == "derive":
            test_derive()

        elif args.endpoint == "preprocess":
            test_preprocess(amount=args.amount)

        elif args.endpoint == "metadata":
            test_metadata(amount=args.amount)

        elif args.endpoint == "payloads":
            test_payloads(amount=args.amount)

        elif args.endpoint == "parse":
            # Test with unsigned transaction
            print("=== Testing UIGNED Transaction Parsing ===")
            test_parse(EXAMPLE_UNSIGNED_TX, signed=False)

            # Test with signed transaction
            print("\n=== Testing SIGNED Transaction Parsing ===")
            test_parse(EXAMPLE_SIGNED_TX, signed=True)

        elif args.endpoint == "combine":
            # Test combine endpoint
            test_combine(EXAMPLE_UNSIGNED_TX, EXAMPLE_SIGNED_HASH)

        elif args.endpoint == "hash":
            # Test hash endpoint
            test_hash(EXAMPLE_SIGNED_TX)

        elif args.endpoint == "submit":
            # Test submit endpoint
            test_submit(EXAMPLE_SIGNED_TX)

        elif args.endpoint == "all":
            print("\nRunning all endpoints...\n")

            # Test derive endpoint
            test_derive()

            # Test preprocess endpoint
            test_preprocess(amount=args.amount)

            # Test metadata endpoint
            test_metadata(amount=args.amount)

            # Test payloads endpoint
            test_payloads(amount=args.amount)

            # Test parse endpoint with unsigned transaction
            print("\n=== Testing UNSIGNED Transaction Parsing ===")
            test_parse(EXAMPLE_UNSIGNED_TX, signed=False)

            # Test combine endpoint (commented by default)
            print("\n[Skipping combine - requires real signature]")

            # Test parse endpoint with signed transaction
            print("\n=== Testing SIGNED Transaction Parsing ===")
            test_parse(EXAMPLE_SIGNED_TX, signed=True)

            # Test hash endpoint (commented by default)
            print("[Skipping hash - requires real signed transaction]")

            # Test submit endpoint (commented by default)
            print("[Skipping submit - would submit to network]")

            print(
                "\nNote: Some endpoints skipped as they require actual transaction data"
            )
            print(
                "from previous steps. Run them individually when you have the required data."
            )

    except requests.exceptions.ConnectionError:
        print(f"\nError: Could not connect to {BASE_URL}")
        print("Make sure your Rosetta node is running")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
