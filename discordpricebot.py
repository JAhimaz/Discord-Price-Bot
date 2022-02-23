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
from calculateTokenPrice import calcSell
from getTokenABI import getTokenABI

# Initialisation
load_dotenv()
ps = PancakeSwapAPI()

# Logging ===========================
def configureLogging():
    logFormatter = logging.Formatter("%(levelname)s - %(asctime)s --> %(message)s")
    
    fileHandler = RotatingFileHandler("logs/output.log", mode="a+", maxBytes=10*1024*1024, backupCount=3)
    # fileHandler = RotatingFileHandler("/home/app/logs/output.log", mode="a+", maxBytes=10*1024*1024, backupCount=3)
    fileHandler.setFormatter(logFormatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(logFormatter)

    log = logging.getLogger()
    log.setLevel(logging.INFO)
    log.addHandler(streamHandler)
    log.addHandler(fileHandler)
#  =================================

configureLogging()

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
PANCAKEROUTER_ADDR = os.getenv("PANCAKEROUTER_ADDR")
CHECKSUM_PANCAKESWAP_ADDR = Web3.toChecksumAddress(PANCAKEROUTER_ADDR)
DISCORD_CHANNELS = json.loads(os.getenv("DISCORD_CHANNEL")) # Discord Channel ID to relay messages
CHECKSUM_TOKEN_ADDR = Web3.toChecksumAddress(TOKEN_ADDR) # CHECKSUM address of Token (For Web3)
TOKEN_DECIMALS = int(os.getenv("TOKEN_DECIMALS"))
INCLUDE_TAX = False
TAX_AMT = float(os.getenv("TAX_AMT"))
HAS_BURN = True

web3 = Web3(Web3.HTTPProvider("https://bsc-dataseed.binance.org/")) # Accessing the mainnet of BSC
# web3 = Web3(Web3.WebsocketProvider("wss://bsc-ws-node.nariox.org:443")) # Accessing the mainnet of BSC


async def StartScan(bot):
    # await channel.send('[{0} HAS STARTED (PYTHON)]'.format(bot.user))
    try:
        abi = getTokenABI(TOKEN_ADDR, API_KEY_BSC)
    except:
        logging.info("Failed to get ABI")

    if(abi): # If valid response from BSCScan
        contract = web3.eth.contract(address=CHECKSUM_TOKEN_ADDR, abi=abi) # Create the contract variable using the ABI and Token Address
        try:
            PANCAKESWAP_ABI = getTokenABI(PANCAKEROUTER_ADDR, API_KEY_BSC)
        except:
            logging.info("Failed to get ABI")

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

// NUMBER OF CHANNELS: {len(DISCORD_CHANNELS)}\n

CURRENT BLOCK ON BSC: {CURRENT_BLOCK}


        '''

        logging.info(startupMessage)

        while(True):
            # checkerBlock = web3.eth.block_number
            
            logging.info(f"Current Block: {CURRENT_BLOCK}")
            
            try:
                bnbPrice = calcSell(tokenAddress=BNB_ADDR, pancakeswapABI=PANCAKESWAP_ABI, output=Web3.toChecksumAddress("0xe9e7cea3dedca5984780bafc599bd69add087d56"))
            except:
                logging.info("Error Getting BNB Price")
                continue

            try:
                tokenCost = (calcSell(tokenAddress=CHECKSUM_TOKEN_ADDR, pancakeswapABI=PANCAKESWAP_ABI, output=BNB_ADDR))
                tokenPrice = float(tokenCost / (10 ** 9)) * bnbPrice
            except:
                logging.info("Error Getting Token Price")
                continue

            try:
                totalSupply = contract.functions.totalSupply().call() / (10 ** 9)
            except:
                logging.info("Error Getting Total Supply")
                continue
                
                

            if(HAS_BURN):
                try:
                    burntSupply = contract.functions.balanceOf(Web3.toChecksumAddress(BURN_ADDR)).call() / (10 ** 9)
                    currentSupply = totalSupply - burntSupply
                except:
                    logging.info("Error calculating current supply")
                    continue
            else:
                currentSupply = totalSupply

            # Transfers List (List of Transfers on Each Block from EGT)

            # Get all transfers from Current Block to the "latest" block on BSC related to EGT (Past Events)

            transfers = []

            topics = ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]
            try:
                transfers = web3.eth.get_logs({'fromBlock': CURRENT_BLOCK, 'toBlock': 'latest', 'topics': topics, 'address': CHECKSUM_TOKEN_ADDR})
            except:
                CURRENT_BLOCK = web3.eth.block_number
                logging.info(f"Exceeded BSCScan RPC Range. Setting NEW Current Block: {CURRENT_BLOCK}")
                transfers = web3.eth.get_logs({'fromBlock': CURRENT_BLOCK, 'toBlock': 'latest', 'topics': topics, 'address': CHECKSUM_TOKEN_ADDR})

            # For each Transfer from the range of Blocks
            # logging.info(transfers[0])

            for transfer in transfers:
                transferFromAddr = "0x" + str(transfer['topics'][1].hex())[-40:]
                blockNumber = transfer['blockNumber'] # The Block Number with the EGT Transaction
                if(transferFromAddr == PANCAKESWAP_ADDR):
                    walletAddr = "0x" + str(transfer['topics'][2].hex())[-40:] # The wallet that purchased the EGT
                    amountEGT = round(int(transfer['data'], 16) / (10 ** TOKEN_DECIMALS), 3) # The Amount of EGT Purchased
                    amountPurchasedUSD = round(amountEGT * float(tokenPrice), 2) # The Amount of EGT Purchased (IN USD)
                    amountInBNB = round(float(amountPurchasedUSD) / float(bnbPrice), 4) # The Amount of EGT Purchased (IN BNB)

                    # logging.info(amountEGT)

                    if(not INCLUDE_TAX):
                        amountEGT = round((amountEGT/100) * (100 + TAX_AMT), 2)
                        amountPurchasedUSD = round((amountPurchasedUSD/100) * (100 + TAX_AMT), 2)
                        amountInBNB = round((amountInBNB/100) * (100 + TAX_AMT), 4)

                    # Possibility to change as sometimes a new transaction can be written on the same block but not pulled up. Might change to check the last
                    # Transaction Hash to fix this if it is too prevalent.

                    if(blockNumber == CURRENT_BLOCK): # Skips Sending the Message if the Block is the same Block
                        logging.info("No Changes")
                        continue
                    
                    logging.info(f"Buy of {amountPurchasedUSD}")

                    if(float(amountPurchasedUSD) > float(ALERT_AMOUNT)): # Checks if the amount Purchased in USD is greater than the Alert Amount

                        logging.info(f"New Buy of {amountPurchasedUSD}")

                        marketCap = float(tokenPrice) * currentSupply
                        try:
                            walletAmount = contract.functions.balanceOf(Web3.toChecksumAddress(walletAddr)).call() / (10 ** 9)
                            isNewBuyer = CheckHolderStatus(walletAmount, amountEGT)
                        except:
                            logging.info("Error getting Wallet Amount (Skipping)")
                            walletAmount = 0
                            isNewBuyer = "Error Getting Wallet Status"


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
                        for dchannel in DISCORD_CHANNELS:
                            channel = bot.get_channel(int(dchannel)) # Gets the channel to post to
                            try:
                                await channel.send(message)
                            except:
                                logging.info(f"Error Sending Message to Channel: {channel}")
                    
                if(blockNumber > CURRENT_BLOCK):
                    logging.info(f"Updating Block Number to: {blockNumber}")
                    CURRENT_BLOCK = blockNumber

            await asyncio.sleep(5)

    else:
        
        logging.info("[Failed to Connect to Web3 Services]")


class MyClient(discord.Client):
    async def on_ready(self):
        
        logging.info('[{0} HAS STARTED]'.format(self.user))
        await StartScan(self)

client = MyClient()
client.run(os.getenv("DISCORD_BOT_TOKEN"))




