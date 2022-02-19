from web3 import Web3
import requests
import json

def getTokenABI(TOKEN_ADDR, API_KEY):
    TOKEN_ABI_URL = f"https://api.bscscan.com/api?module=contract&action=getabi&address={TOKEN_ADDR}&apikey={API_KEY}" # Fetches the ABI from BSCScan API
    response = requests.get(TOKEN_ABI_URL).json() # Checks for a response
    return json.loads(response['result']) # Store the ABI