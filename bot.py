import discord
import requests
import asyncio
import configparser
import os

from time import sleep, time
from tabulate import tabulate
from bs4 import BeautifulSoup

servers = {"hk": {},"eu": {},"pool": {}}
num_blocks = -1
pool_fee = -1
channel = None

def main():
    client = discord.Client()
    conf = configparser.RawConfigParser()
    conf.read("config.txt")

    BOT_TOKEN = conf.get('bot_conf', 'BOT_TOKEN')
    BLOCKS_CHANNEL = conf.get('bot_conf', 'BLOCKS_CHANNEL')

    @client.event
    async def on_ready():
        print('Logged in as {} <@{}>'.format(client.user.name, client.user.id))
        print('------')

    @client.event
    async def on_message(message):
        if message.content.startswith("!pool"):
            arr = []
            for server in servers:
                arr.append([server, servers[server]["hr"], servers[server]["clients"]])
            msg = tabulate(arr, headers=["Server", "Hashrate", "# miners"])
            await client.send_message(message.channel, "```js\n{}```".format(msg))

    async def background_update():
        num_blocks_cur = -1
        for server in servers:
            try:
                req = requests.get("https://{}.nimiqpocket.com:8444/api/poolstats".format(server), timeout=5)
            except requests.Timeout:
                print("Couldn't connect to {}".format(server))
                break

            json = req.json()
            servers[server]["hr"] = json["hashRate"]
            servers[server]["clients"] = json["numClients"]
            if server == "hk":
                num_blocks_cur = json["minedBlocks"]
                pool_fee = json["poolFee"]

        await client.wait_until_ready()
        channel = discord.Object(id=BLOCKS_CHANNEL)

        print(channel)
        if num_blocks_cur != num_blocks:
            if channel is not None:
                msg = "`We found Nimiqpocket's #{} block!` :tada:".format(num_blocks_cur)
                await client.send_message(channel, msg)

        await asyncio.sleep(60)

    client.loop.create_task(background_update())
    client.run(BOT_TOKEN)

if __name__ == "__main__":
    while True:
        try:
            main()
        except ConnectionResetError:
            sleep(5)
