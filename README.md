# [XAI](https://xai.games/sentrynodes) node rewards monitor
A simple script to monitor new esXAI token transfers from your node to your wallets

# Requirements
All that you need is Python (tested on Python3.9), Telegram Bot API key, and [ArbiScan](https://arbiscan.io/) API key (it is free)

To obtain the Telegram Bot API key - just message `@BotFather` or [use this link](https://telegram.me/BotFather) and create a new bot. 

IMPORTANT! Open chat with your bot and send /start to the chat!

# Installation
1. Clone this repository to your local machine (`git clone https://github.com/danijcom/xai-node-rewards-monitor.git`)
2. Go to the downloaded folder (`cd xai-node-rewards-monitor`)
3. Install requirements (`python3 -m pip install -r requirements.txt`)
4. Edit `example_config.json` (you can use `nano example_config.json`) (check the config [section below](https://github.com/danijcom/xai-node-rewards-monitor?tab=readme-ov-file#config) to find out the meaning of config values).
5. Rename `example_config.json` to `config.json` (`mv example_config.json config.json`)
6. Start script (`python3 main.py`) (to run it in the background you can use `nohup python3 main.py &` or refer to [this guide](https://medium.com/codex/setup-a-python-script-as-a-service-through-systemctl-systemd-f0cc55a42267) to setup systemd daemon for your script
7. 🥳 Enjoy getting notifications on your esXAI rewards!

# Config
Your config is stored in the `config.json` file.

Main values to edit: 

`api_key` in `bot_setting` section. Put there your bot API key from @BotFather.

`receiver_telegram_id`. Put there user/group Telegram ID to get notifications. If it is the ID of the user - make sure you send `/start` to your bot before running the script. Telegram ID can be obtained using [this bot](https://t.me/myidbot)

`arbiscan_api_key` in `arbitrum` section. Put there your API key from [ArbiScan](https://arbiscan.io/).

`wallets` section:

If you only have 1 wallet with XAI node key - it should look like this:
```
"wallets": {
    "MY_KEY_NAME": "WALLET_ADDRESS",
  }
```

Where `MY_KEY_NAME` is the name (used for notifications only) and `WALLET_ADDRESS` is your Arbitrum address (`0x.....`)


If you have more than 1 key it should look like that:
```
"wallets": {
    "KEY1_NAME": "KEY1_ADDRESS",
    "KEY2_NAME": "KEY2_ADDRESS",
    ...,
    "KEYN_NAME": "KEYN_ADDRESS"
  }
```

Note that [ArbiScan Free Tier](https://docs.arbiscan.io/support/rate-limits) allows you to send about 100.000 requests per day, so if you have more than 130 wallets, you should adjust `checks_timeout_minutes`

Hope you got it!
