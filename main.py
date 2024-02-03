import os.path
import sys
import time
import json
import logging
import requests

from typing import Union
from pathlib import Path
from datetime import datetime

settings_filename = 'config.json'
cache_filename = 'cache.json'
logs_filename = 'app.log'

settings_path = Path().absolute() / settings_filename
cache_path = Path().absolute() / cache_filename
logs_path = Path().absolute() / logs_filename

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(logs_path.resolve()),
        logging.StreamHandler(sys.stdout)
    ]
)


# Convert wei (denomination of ether) to ether 1 Ether is equal to 10^18 Wei
def wei_to_ether(wei_amount):
    ether_amount = int(wei_amount) / 10**18
    return ether_amount


# Get XAI price from Binance API
def get_xai_price():
    url = 'https://api.binance.com/api/v3/ticker/price?symbol=XAIUSDT'
    response = requests.get(url).json()
    return response['price']


# Get token transaction by address and token contract address, requires ArbiScan API key
def get_transactions(address: str, contract: str, api_key: str):
    url = f'https://api.arbiscan.io' \
          f'/api?module=account&action=tokentx' \
          f'&contractaddress={contract}&address={address}' \
          f'&startblock=0&endblock=latest&sort=asc' \
          f'&apikey={api_key}'

    response = requests.get(url).json()
    return response


# Retries wrapper for get_transactions method to handle exceptions
def get_transactions_with_retries(address: str, contract: str, api_key: str, max_retries: int = 10):
    retries = 0
    while retries < max_retries:
        retries += 1

        try:
            response = get_transactions(address, contract, api_key)
            if response['status'] == '1' and response['message'] == 'OK':
                return True, response
            else:
                logging.error(
                    'Failed fetch transactions for address {} (contract: {}): {}'.format(
                        address, contract, response
                    )
                )
        except Exception as ex:
            logging.error(
                'Failed fetch transactions for address {} (contract: {}): {}'.format(
                    address, contract, ex
                )
            )

        time.sleep(5)
    return False, ''


# Send a message to telegram chat id
def send_telegram_message(bot_token: str, chat_id: Union[int, str], text):
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'

    data = {
        'chat_id': int(chat_id),
        'text': text,
        'parse_mode': 'HTML',
        'link_preview_options': {
            'is_disabled': True
        }
    }

    response = requests.post(url, json=data).json()
    return response


# Retries wrapper for send_telegram_message_with_retries method to handle exceptions
def send_telegram_message_with_retries(bot_token: str, chat_id: Union[int, str], text: str, max_retries: int = 10):
    retries = 0
    while retries < max_retries:
        retries += 1

        try:
            response = send_telegram_message(bot_token, chat_id, text)
            if response['ok']:
                logging.info('Telegram notification sent to {}'.format(chat_id))
                return True
            else:
                logging.error('Failed to send Telegram message to {}: {}'.format(chat_id, response))
        except Exception as ex:
            logging.error('Failed to send Telegram message to {}: {}'.format(chat_id, ex))

        time.sleep(5)
    return False


if __name__ == '__main__':
    if not os.path.isfile(settings_path.resolve()):
        logging.error(
            'Config file is not found. '
            'Your config should be in the same directory with this script ({})'.format(settings_path.resolve())
        )
        exit(0)
    if not os.path.isfile(cache_path.resolve()):
        with open(cache_path.resolve(), 'w', encoding='utf-8') as file:
            json.dump({}, file, ensure_ascii=False, indent=4)
            logging.info('Cache file created!')

    logging.info('Monitor started!')

    # Load config and cache from files
    with open(settings_path.resolve(), 'r', encoding='utf-8') as file:
        settings_json = json.load(file)
        logging.info('Settings loaded from {}'.format(settings_path.resolve()))
    with open(cache_path.resolve(), 'r', encoding='utf-8') as file:
        cache_json = json.load(file)
        logging.info('Cache loaded from {}'.format(settings_path.resolve()))

    logging.info('Wallets to monitor: {}'.format(settings_json['wallets']))

    # Infinite loop for wallets monitoring
    while True:
        # Cache for XAI price
        xai_price = None

        # Processing wallets one by one
        for address_name in settings_json['wallets']:
            address = settings_json['wallets'][address_name]
            logging.info('Processing wallet [{}] with address {}'.format(address_name, address))

            # Get transactions from ArbiScan
            status, transactions = get_transactions_with_retries(
                address,
                settings_json['arbitrum']['xai_contract'],
                settings_json['arbitrum']['arbiscan_api_key']
            )

            # Check for success
            if status:
                # Add address to cache if it is a new address
                if address not in cache_json:
                    cache_json[address] = {}

                # Processing each transaction
                for transaction in transactions['result']:
                    transaction_hash = transaction['hash']

                    # Check if it is a new transaction
                    if transaction_hash not in cache_json[address]:
                        logging.info('[{}] New transaction {}'.format(address_name, transaction_hash))

                        if xai_price is None:
                            try:
                                xai_price = float(get_xai_price())
                            except Exception as ex:
                                logging.error('Failed to get XAI price: {}'.format(ex))

                        # Get human readable value in ether
                        amount = wei_to_ether(transaction['value'])
                        # Amount in USD (yep, I know about vesting and all of that, but still its fun to know the price
                        amount_usd = '?' if xai_price is None else xai_price * amount
                        # Transaction on ArbiScan
                        transaction_url = 'https://arbiscan.io/tx/' + transaction['hash']
                        # Convert timestamp to readable date
                        date_str = datetime.utcfromtimestamp(
                            int(transaction['timeStamp'])
                        ).strftime('%Y-%m-%d %H:%M:%S')

                        # Add transaction to cache
                        cache_json[address][transaction_hash] = {
                            'amount': '{:.2f}'.format(amount),
                            'amount_wei': transaction['value'],
                            'amount_usd': None if amount_usd == '?' else amount_usd,
                            'timestamp': transaction['timeStamp'],
                            'humanized_date': date_str
                        }

                        # Yep, HTML, I hate manually escape special symbols
                        message_text = '🤑 <b>New {} token transfer!</b>\n\n' \
                                       '🔑 Key name: <b>{}</b>\n' \
                                       '💰 Amount: <b>{:.2f} {}</b>\n' \
                                       '💲 Amount USD: <b>${} {}</b>\n' \
                                       '📆 Date: <code>{}</code>\n\n' \
                                       '📎 <b>Transaction:</b> {}'.format(
                                            transaction['tokenName'],
                                            address_name,
                                            amount,
                                            transaction['tokenName'],
                                            amount_usd if type(amount_usd) == str else '{:.1f}'.format(amount_usd),
                                            '' if xai_price is None else '(1 XAI = ${:.2f})'.format(xai_price),
                                            date_str,
                                            transaction_url,
                                       )

                        # Send notification
                        message_sent = send_telegram_message_with_retries(
                            settings_json['bot_settings']['api_key'],
                            settings_json['bot_settings']['receiver_telegram_id'],
                            message_text
                        )
                        # Since our main goal is to notify for a new transactions,
                        # we will not add transaction to cache if we failed to notify
                        if not message_sent:
                            cache_json[address].pop(transaction_hash)

            # Update cache file
            with open(cache_path.resolve(), 'w', encoding='utf-8') as file:
                json.dump(cache_json, file, ensure_ascii=False, indent=4)
                logging.info('Cache saved!')
            # We should sleep for some time between requests to ArbiScan API
            time.sleep(1)

        # Sleep for some time in order to not spam API requests
        logging.info('Sleep for {} minutes..'.format(settings_json['checks_timeout_minutes']))
        time.sleep(settings_json['checks_timeout_minutes'] * 60)
