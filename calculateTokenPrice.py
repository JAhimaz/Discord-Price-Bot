from web3 import Web3

def calcSell(tokenAddress, pancakeswapABI, output):
    routerPCS = Web3.toChecksumAddress("0x10ed43c718714eb63d5aa57b78b54704e256024e")
    routerContract = web3.eth.contract(address=routerPCS, abi=pancakeswapABI)
    price = routerContract.functions.getAmountsOut(1, [tokenAddress, output]).call()
    # normalisedPrice = web3.fromWei(price[1], 'Ether')
    return price[1]

web3 = Web3(Web3.HTTPProvider("https://bsc-dataseed.binance.org/")) # Accessing the mainnet of BSC