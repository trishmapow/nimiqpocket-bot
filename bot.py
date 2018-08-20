import discord
import requests
import asyncio
import configparser
import os

from time import sleep, time, strftime
from datetime import datetime
from tabulate import tabulate
from bs4 import BeautifulSoup

#servers = {"us": {}}
num_blocks = -1
#pool_fee = -1
channel = None
pool_msg = ""

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
            await client.send_message(message.channel, "```js\n{}```".format(pool_msg))

    async def background_update():
        global num_blocks
        global pool_msg

        await client.wait_until_ready()
        channel = discord.Object(id=BLOCKS_CHANNEL)

        while not client.is_closed:
            num_blocks_cur = -1
            sum_hr = 0
            sum_clients = 0

            try:
                req = requests.get("https://api.nimiqpocket.com:8080/api/poolstats", timeout=5)
                json = req.json()
            except:
                print("Couldn't connect to API")
                await asyncio.sleep(15)
                break

            hr = int(json["totalHashrate"])
            if (hr < 1e6):
                hr = str(round(hr/1e3,2))+"kH/s"
            else:
                hr = str(round(hr/1e6,2))+"MH/s"
            clients = json["totalClients"]
            users = json["totalUsers"]

            num_blocks_cur = json["totalBlocksMined"]

            if num_blocks_cur > num_blocks:
                num_blocks = num_blocks_cur
                if channel is not None:
                    msg = "`We found Nimiqpocket's #{} block! ".format(num_blocks_cur)
                    try:
                        r = requests.get("https://api.nimiqx.com/account-blocks/NQ37+47US+CL1J+M0KQ+KEY3+YQ4G+KGHC+VPVF+8L02", timeout=5)
                        j = r.json()[0]
                        height = str(j["height"])
                        diff = str(round(float(j["difficulty"])))
                        time = j["timestamp"]
                        timef = datetime.utcfromtimestamp(int(time)).strftime('%Y-%m-%d %H:%M:%S GMT')

                        msg += "(Height: " + height + ", " + "Diff: " + diff + ", " + timef + ")` :tada:"
                    except (requests.Timeout, requests.exceptions.ConnectionError):
                        print("Couldn't connect to Nimiqx API")
                    await client.send_message(channel, msg)

            pool_msg = "Hashrate: {}\nClients/users: {}/{}\nBlocks: {}".format(hr,clients,users,num_blocks_cur)

            await asyncio.sleep(60)

    client.loop.create_task(background_update())
    client.run(BOT_TOKEN)

if __name__ == "__main__":
    while True:
        try:
            main()
        except ConnectionResetError:
            sleep(10)
