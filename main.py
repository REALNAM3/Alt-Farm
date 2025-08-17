import discord
from discord import app_commands
import aiohttp
import asyncio
import datetime
import os
from flask import Flask
from threading import Thread
import subprocess

subprocess.Popen(["python", "main2.py"])

app = Flask('')

@app.route('/')
def home():
    return "Alt farm"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

ALL_MODS = {
    "Chase": [22808138, 4782733628, 7447190808, 3196162848],
    "Orion": [547598710, 5728889572, 4652232128, 7043591647, 4149966999, 7209929547, 7043958628, 7418525152, 3774791573, 8606089749],
    "LisNix": [162442297, 702354331],
    "Nwr": [307212658, 5097000699, 4923561416],
    "Gorilla": [514679433, 2431747703, 4531785383],
    "Typhon": [2428373515],
    "Vic": [839818760],
    "Erin": [2465133159],
    "Ghost": [7558211130],
    "Sponge": [376388734, 5157136850, 8786504626],
    "Gora": [589533315, 567497793],
}

UNKNOWN_MODS = {
    "NNs": [
        7547477786, 7574577126, 2043525911, 5816563976, 240526951, 7587479685,
        1160595313, 7876617827, 7693766866, 2568824396, 7604102307, 7901878324,
        5087196317, 7187604802, 7495829767, 7718511355, 7928472983, 7922414080,
        7758683476, 9154975419
    ]
}

BATCH_SIZE = 100

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.checking_task = None

    async def on_ready(self):
        print(f"Bot connected as {self.user} ({self.user.id})")

    async def setup_hook(self):
        await self.tree.sync()

    async def fetch_presence(self, user_ids):
        """Obtiene presencia en batches para evitar errores."""
        all_presences = []
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(user_ids), BATCH_SIZE):
                batch = user_ids[i:i+BATCH_SIZE]
                try:
                    async with session.post("https://presence.roblox.com/v1/presence/users", json={"userIds": batch}) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json()
                        all_presences.extend(data.get("userPresences", []))
                except Exception as e:
                    print(f"[fetch_presence] Error: {e}")
        return {p["userId"]: p["userPresenceType"] for p in all_presences}

    async def fetch_usernames(self, user_ids):
        usernames = {}
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(user_ids), BATCH_SIZE):
                batch = user_ids[i:i+BATCH_SIZE]
                try:
                    async with session.post("https://users.roblox.com/v1/users", json={"userIds": batch}) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json()
                        for u in data.get("data", []):
                            usernames[u["id"]] = u.get("name", "Unknown")
                except Exception as e:
                    print(f"[fetch_usernames] Error: {e}")
        return usernames

    async def build_status(self, mod_dict):
        all_user_ids = list({uid for ids in mod_dict.values() for uid in ids})
        presence_dict = await self.fetch_presence(all_user_ids)
        username_dict = await self.fetch_usernames(all_user_ids)

        message_lines = []
        any_in_game = False

        message_lines.append("__**Mods:**__")
        for mod_name, user_ids in mod_dict.items():
            message_lines.append(f"**{mod_name}**")
            for uid in user_ids:
                username = username_dict.get(uid, "Unknown")
                presence_code = presence_dict.get(uid, 0)

                if presence_code == 1:
                    line = f"```ini\n[Online]: {username}\n```"
                elif presence_code == 2:
                    line = f"```diff\n+ In Game: {username}\n```"
                    any_in_game = True
                elif presence_code == 3:
                    line = f"```fix\nIn Studio: {username}\n```"
                else:
                    line = f"```diff\n- Offline: {username}\n```"
                message_lines.append(line)
            message_lines.append("")

        status_line = "**Status: Unalt Farmable**" if any_in_game else "**Status: Alt Farmable**"
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        message_lines.append(status_line)
        message_lines.append(f"*Last Update: {timestamp}*")

        return "\n".join(message_lines)

    async def build_known_mod_status(self):
        return await self.build_status(ALL_MODS)

    async def build_unknown_mod_status(self):
        return await self.build_status(UNKNOWN_MODS)

client = MyClient()

@client.tree.command(name="mods", description="Shows if a known mod is online")
async def mods(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    content = await client.build_known_mod_status()
    await interaction.followup.send(content)

@client.tree.command(name="unknownmods", description="Shows if an unknown mod is online")
async def unknownmods(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    content = await client.build_unknown_mod_status()
    await interaction.followup.send(content)

client.run(os.getenv("BOT_TOKEN"))
