# Discord.py Import
from tabnanny import check
import discord
# For reading .env files
from dotenv.main import load_dotenv
import os
# Logging
import logging
from logging.handlers import RotatingFileHandler
# Web3 & Token related
from web3 import Web3
from web3.logs import DISCARD
import requests
import json
from pythonpancakes import PancakeSwapAPI
# Misc
import asyncio

# Initialisation
load_dotenv()
ps = PancakeSwapAPI()

# Logging ===========================
def configureLogging():
    logFormatter = logging.Formatter("%(levelname)s - %(asctime)s --> %(message)s")

    fileHandler = RotatingFileHandler("/home/app/logs/output.log", mode="a+", maxBytes=10*1024*1024, backupCount=3)
    fileHandler.setFormatter(logFormatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(logFormatter)

    log = logging.getLogger()
    log.setLevel(logging.INFO)
    log.addHandler(streamHandler)
    log.addHandler(fileHandler)
#  =================================

def CheckHolderStatus(walletAmount, buyAmount):
    if(walletAmount - buyAmount < 100.00):
        return "NEW BUYER"
    else:
        return "RETURNING BUYER"


# Variable Declaration
API_KEY_BSC = os.getenv('API_KEY_BSC') # API Key for BSC (Used for ABI)
TOKEN_ADDR = os.getenv("TOKEN_ADDR") # TOKEN Address
BNB_ADDR = os.getenv("BNB_ADDR") # BNB Address
BURN_ADDR = os.getenv("BURN_ADDR")
PANCAKESWAP_ADDR = os.getenv("PANCAKESWAP_ADDR") # PancakeSwap SWAP Address
DISCORD_CHANNEL = os.getenv("DISCORD_CHANNEL") # Discord Channel ID to relay messages
CHECKSUM_TOKEN_ADDR = Web3.toChecksumAddress(TOKEN_ADDR) # CHECKSUM address of Token (For Web3)
TOKEN_DECIMALS = int(os.getenv("TOKEN_DECIMALS"))
INCLUDE_TAX = False
TAX_AMT = float(os.getenv("TAX_AMT"))
HAS_BURN = True

web3 = Web3(Web3.HTTPProvider("https://bsc-dataseed.binance.org/")) # Accessing the mainnet of BSC
# web3 = Web3(Web3.WebsocketProvider("wss://bsc-ws-node.nariox.org:443")) # Accessing the mainnet of BSC


async def StartScan(bot):
    channel = bot.get_channel(int(DISCORD_CHANNEL)) # Gets the channel to post to
    # await channel.send('[{0} HAS STARTED (PYTHON)]'.format(bot.user))

    TOKEN_ABI_URL = f"https://api.bscscan.com/api?module=contract&action=getabi&address={TOKEN_ADDR}&apikey={API_KEY_BSC}" # Fetches the ABI from BSCScan API
    response = requests.get(TOKEN_ABI_URL).json() # Checks for a response

    if(response): # If valid response from BSCScan

        abi = json.loads(response['result']) # Store the ABI
        contract = web3.eth.contract(address=CHECKSUM_TOKEN_ADDR, abi=abi) # Create the contract variable using the ABI and Token Address

        # CURRENT_BLOCK = int(os.getenv("INITIAL_BLOCK")) # Gets the Initial Block Number Manually
        CURRENT_BLOCK = web3.eth.block_number # Gets the Latest Block Number from the BSC Network
        ALERT_AMOUNT = float(os.getenv("ALERT_AMOUNT")) # The Alert Amount in USD to when the Bot sends a message

        TOKEN_NAME = os.getenv("TOKEN_NAME") # The Token Name 
        TOKEN_SYMBOL = os.getenv("TOKEN_SYMBOL") # The Token Symbol

        startupMessage = f'''
[BSC BUY BOT DETAILS]

TOKEN NAME: {TOKEN_NAME}
TOKEN SYMBOL: {TOKEN_SYMBOL}
TOKEN ADDR: {TOKEN_ADDR}
TOKEN INCLUDE TAX: {INCLUDE_TAX}
TOKEN TAX AMOUNT: {TAX_AMT}

CURRENT BLOCK ON BSC: {CURRENT_BLOCK}
        '''

        print(startupMessage)

        while(True):
            # checkerBlock = web3.eth.block_number
            logging.info(f"Current Block: {CURRENT_BLOCK}") # Logs the current Block
            print(f"Current Block: {CURRENT_BLOCK}")
        
            # Get the price of ELONGOAT
            try:
                tokenData = ps.tokens(TOKEN_ADDR) # Gets the Price of the Token from Pancakeswap API
            except:
                logging.info("Error Getting Token Price")
                print("Error Getting Token Price")
            tokenPrice = tokenData['data']['price']

            # Get the price of BNB
            try:
                bnbData = ps.tokens(BNB_ADDR) # Gets the Price of BNB from Pancakeswap API
            except:
                logging.info("Error Getting BNB Price")
                print("Error Getting BNB Price")
            bnbPrice = bnbData['data']['price']

            totalSupply = contract.functions.totalSupply().call() / (10 ** 9)

            if(HAS_BURN):
                burntSupply = contract.functions.balanceOf(Web3.toChecksumAddress(BURN_ADDR)).call() / (10 ** 9)
                currentSupply = totalSupply - burntSupply
            else:
                currentSupply = totalSupply

            # Transfers List (List of Transfers on Each Block from EGT)

            # Get all transfers from Current Block to the "latest" block on BSC related to EGT (Past Events)

            transfers = []

            topics = ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]
            try:
                transfers = web3.eth.get_logs({'fromBlock': CURRENT_BLOCK, 'toBlock': 'latest', 'topics': topics, 'address': CHECKSUM_TOKEN_ADDR})
            except ValueError:
                CURRENT_BLOCK = web3.eth.block_number
                print(f"Exceeded BSCScan RPC Range. Setting NEW Current Block: {CURRENT_BLOCK}")
                transfers = web3.eth.get_logs({'fromBlock': CURRENT_BLOCK, 'toBlock': 'latest', 'topics': topics, 'address': CHECKSUM_TOKEN_ADDR})

            # For each Transfer from the range of Blocks

            for transfer in transfers:
                transferFromAddr = "0x" + str(transfer['topics'][1].hex())[-40:]
                blockNumber = transfer['blockNumber'] # The Block Number with the EGT Transaction
                if(transferFromAddr == PANCAKESWAP_ADDR):
                    walletAddr = "0x" + str(transfer['topics'][2].hex())[-40:] # The wallet that purchased the EGT
                    amountEGT = round(int(transfer['data'], 16) / (10 ** TOKEN_DECIMALS), 3) # The Amount of EGT Purchased
                    amountPurchasedUSD = round(amountEGT * float(tokenPrice), 2) # The Amount of EGT Purchased (IN USD)
                    amountInBNB = round(float(amountPurchasedUSD) / float(bnbPrice), 4) # The Amount of EGT Purchased (IN BNB)

                    # print(amountEGT)

                    if(not INCLUDE_TAX):
                        amountEGT = round((amountEGT/100) * (100 + TAX_AMT), 2)
                        amountPurchasedUSD = round((amountPurchasedUSD/100) * (100 + TAX_AMT), 2)
                        amountInBNB = round((amountInBNB/100) * (100 + TAX_AMT), 4)

                    # Possibility to change as sometimes a new transaction can be written on the same block but not pulled up. Might change to check the last
                    # Transaction Hash to fix this if it is too prevalent.

                    if(blockNumber == CURRENT_BLOCK): # Skips Sending the Message if the Block is the same Block
                        print("No Changes")
                        continue
                    
                    print(f"Buy of {amountPurchasedUSD}")

                    if(float(amountPurchasedUSD) > float(ALERT_AMOUNT)): # Checks if the amount Purchased in USD is greater than the Alert Amount

                        print(f"New Buy of {amountPurchasedUSD}")

                        marketCap = float(tokenPrice) * currentSupply
                        walletAmount = contract.functions.balanceOf(Web3.toChecksumAddress(walletAddr)).call() / (10 ** 9)
                        isNewBuyer = CheckHolderStatus(walletAmount, amountEGT)

                        D_SYMB = "🟩"

                        message = f'''
⸻ **[ NEW BUY FOR {TOKEN_NAME} ]** ⸻
{D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB}

**{TOKEN_SYMBOL} BOUGHT**: {amountEGT:,} **{TOKEN_SYMBOL}**
**FOR**: {amountInBNB} **BNB** (${amountPurchasedUSD:,})

**Price**: `${round(float(tokenPrice), 7)}`
**Marketcap**: `${round(marketCap, 0):,}`

**Buyer ({isNewBuyer})**:
`{walletAddr}`

{D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB} {D_SYMB}
''' 
                        await channel.send(message)
                    
                if(blockNumber > CURRENT_BLOCK):
                    print(f"Updating Block Number to: {blockNumber}")
                    CURRENT_BLOCK = blockNumber

            await asyncio.sleep(5)

    else:
        logging.info("[Failed to Connect to Web3 Services]")
        print("[Failed to Connect to Web3 Services]")


class MyClient(discord.Client):
    async def on_ready(self):
        logging.info('[{0} HAS STARTED]'.format(self.user))
        print('[{0} HAS STARTED]'.format(self.user))
        await StartScan(self)

client = MyClient()
client.run(os.getenv("DISCORD_BOT_TOKEN"))



