import discord
import requests
import asyncio
import configparser
import os
import sqlite3

from time import sleep, time, strftime, localtime, asctime
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

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS `w` (`id` VARCHAR(18) PRIMARY KEY, `address` VARCHAR(36))')
    conn.commit()

    def get_address(id):
        c.execute('SELECT * FROM `w` WHERE `id`={}'.format(id))
        res = c.fetchall()
        if (len(res) == 0):
            return ""
        else:
            return res[0][1]

    def set_address(id,address):
        c.execute("INSERT OR IGNORE INTO `w` (`id`,`address`) VALUES ('{}','');".format(id))
        c.execute("UPDATE `w` SET `address`='{}' WHERE `id`='{}';".format(address,id))
        conn.commit()

    def format_hr(hr):
        hr = int(hr)
        if (hr < 1e6):
            hr = str(round(hr/1e3,2))+"kH/s"
        else:
            hr = str(round(hr/1e6,2))+"MH/s"
        return hr

    @client.event
    async def on_ready():
        print('Logged in as {} <@{}>'.format(client.user.name, client.user.id))
        print('------')

    @client.event
    async def on_message(message):
        if message.content.startswith("!pool"):
            await client.send_message(message.channel, "```js\n{}```".format(pool_msg))

        if message.content.startswith("!setaddr"):
            msg = message.content.split(" ")
            if len(msg) == 2 and len(msg[1]) == 36:
                addr = msg[1]
            elif len(msg) == 10 and len(''.join(msg[1:])) == 36:
                addr = ''.join(msg[1:])
            else:
                await client.send_message(message.channel, "```Usage: !setaddr [address]```")
                return
            set_address(message.author.id,addr)
            await client.send_message(message.channel, "```Set your address to {}```".format(addr))

        if message.content.startswith("!me"):
            addr = get_address(message.author.id)
            if addr == "":
                await client.send_message(message.channel, "```Please use !setaddr first.```")
            else:
                try:
                    r = requests.get("https://api.nimiqpocket.com:8080/api/device/{}".format(addr), timeout=5)
                    j = r.json()
                except:
                    await client.send_message(message.channel, "```Couldn't reach API```")
                    print("Couldn't reach API")
                    return

                table = []

                activeDevices = j["activeDevices"]
                for device in activeDevices:
                    hash = format_hr(device["hashrate"])
                    name = device["deviceName"]
                    table.append([name, hash])

                numDevices = j["totalActiveDevices"]
                totalHash = format_hr(j["totalActiveDevicesHashrate"])

                table.append(["TOTAL", "{} miners @ {}".format(numDevices,totalHash)])

                msg = tabulate(table, headers=["Name","Hashrate"])
                await client.send_message(message.channel, "```js\n{}```".format(msg))

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
                        r = requests.get("https://api.nimiqx.com/account-blocks/NQ37+47US+CL1J+M0KQ+KEY3+YQ4G+KGHC+VPVF+8L02/?api_key={}".format("50bd2d069fe5624a8e5a74b91dc9f315"), timeout=5)
                        j = r.json()[0]
                        height = str(j["height"])
                        diff = str(round(float(j["difficulty"])))
                        time = j["timestamp"]
                        timef = datetime.utcfromtimestamp(int(time)).strftime('%Y-%m-%d %H:%M:%S GMT')

                        msg += "(Height: " + height + ", " + "Diff: " + diff + ", " + timef + ")` :tada:"
                    except:
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
