import discord
import aiohttp
import asyncio
import datetime
import os
import subprocess
from discord import app_commands
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()
URI = os.getenv("MONGO_URI")
TOKEN = os.getenv("BOT_TOKEN")

subprocess.Popen(["python", "Account_Detector1.1.py"])

app = Flask('')

@app.route('/')
def home():
    return "Alt farm"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

def get_mods_db():
    mongDB = MongoClient(URI, server_api=ServerApi('1'))
    db = mongDB["mods_db"]
    mods_collection = db["mods"]

    KNOWN_MODS = []
    UNKNOWN_MODS = []

    MOD_DB1 = mods_collection.find_one({"type": "known"})
    MOD_DB2 = mods_collection.find_one({"type": "unknown"})

    if MOD_DB1 and "mods" in MOD_DB1:
        for mod_name, mod_ids in MOD_DB1["mods"].items():
            KNOWN_MODS.append((mod_name, mod_ids))

    if MOD_DB2 and "mods" in MOD_DB2:
        for mod_name, mod_ids in MOD_DB2["mods"].items():
            UNKNOWN_MODS.append((mod_name, mod_ids))

    return KNOWN_MODS, UNKNOWN_MODS

BATCH_SIZE = 50

async def fetch_presences(user_ids: list[int], session: aiohttp.ClientSession) -> dict:
    presence_dict = {}
    for i in range(0, len(user_ids), BATCH_SIZE):
        batch = user_ids[i:i + BATCH_SIZE]
        try:
            async with session.post(
                "https://presence.roblox.com/v1/presence/users",
                json={"userIds": batch}
            ) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()
                for user in data.get("userPresences", []):
                    presence_dict[int(user["userId"])] = user
        except Exception as e:
            print(f"[fetch_presences] Error fetching batch {batch}: {e}")
    return presence_dict

async def fetch_usernames(user_ids: list[int], session: aiohttp.ClientSession) -> dict:
    usernames = {}
    for i in range(0, len(user_ids), BATCH_SIZE):
        batch = user_ids[i:i + BATCH_SIZE]
        tasks = []
        for uid in batch:
            tasks.append(session.get(f"https://users.roblox.com/v1/users/{uid}"))
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for idx, resp in enumerate(responses):
            uid = batch[idx]
            try:
                if isinstance(resp, Exception):
                    usernames[uid] = "Unknown"
                    continue
                async with resp:
                    if resp.status == 200:
                        user_data = await resp.json()
                        usernames[uid] = user_data.get("name", "Unknown")
                    else:
                        usernames[uid] = "Unknown"
            except:
                usernames[uid] = "Unknown"
    return usernames

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

    async def build_mod_status(self, known=True) -> str:
        KNOWN_MODS, UNKNOWN_MODS = get_mods_db()
        mod_list = KNOWN_MODS if known else UNKNOWN_MODS
        all_mods = list({uid for mod_name, ids in KNOWN_MODS + UNKNOWN_MODS for uid in ids})

        async with aiohttp.ClientSession() as session:
            presence_dict = await fetch_presences(all_mods, session)
            usernames = await fetch_usernames(all_mods, session)

        message_lines = []
        any_in_game = False
        title = "Known Mods" if known else "Unknown Mods"
        message_lines.append(f"__**{title}:**__")

        for mod_name, user_ids in mod_list:
            message_lines.append(f"**{mod_name}**")
            for uid in user_ids:
                presence_code = presence_dict.get(uid, {}).get("userPresenceType", 0)
                username = usernames.get(uid, "Unknown")

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

client = MyClient()

@client.tree.command(name="mods", description="Shows if a known mod is online")
async def mods(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    content = await client.build_mod_status(known=True)
    await interaction.followup.send(content)

@client.tree.command(name="unknownmods", description="Shows if an unknown mod is online")
async def unknownmods(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    content = await client.build_mod_status(known=False)
    await interaction.followup.send(content)

@client.tree.command(name="checkmods", description="Checks known mods every minute")
async def checkmods(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    message = await interaction.followup.send("Started checking...")

    async def periodic_check(msg):
        current_msg = msg
        while True:
            try:
                content = await client.build_mod_status(known=True)
                await current_msg.delete()
                current_msg = await msg.channel.send(content)
            except Exception as e:
                print(f"[checkmods] Error in periodic_check: {e}")
                break
            await asyncio.sleep(60)

    if client.checking_task is None or client.checking_task.done():
        client.checking_task = asyncio.create_task(periodic_check(message))
    else:
        await interaction.followup.send("The checking is already active.")

@client.tree.command(name="modson", description="Checks if any mod (known or unknown) is in game")
async def modson(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    KNOWN_MODS, UNKNOWN_MODS = get_mods_db()
    ALL_MODS = list({uid for mod_name, ids in KNOWN_MODS + UNKNOWN_MODS for uid in ids})
    valid_user_ids = [uid for uid in ALL_MODS if uid > 0]

    async with aiohttp.ClientSession() as session:
        presence_dict = await fetch_presences(valid_user_ids, session)
        usernames = await fetch_usernames(valid_user_ids, session)

    message_lines = []
    any_found = False

    for label, mod_list in [("Known Mods", KNOWN_MODS), ("Unknown Mods", UNKNOWN_MODS)]:
        temp_lines = []
        for mod_name, user_ids in mod_list:
            mod_lines = []
            for uid in user_ids:
                presence_info = presence_dict.get(uid)
                if presence_info and presence_info["userPresenceType"] in [1, 2]:
                    username = usernames.get(uid, "Unknown")
                    if presence_info["userPresenceType"] == 2:
                        mod_lines.append(f"```diff\n+(In Game) {username}\n```")
                    else:
                        mod_lines.append(f"```ini\n[Online]: {username}\n```")
                    any_found = True
            if mod_lines:
                temp_lines.append(f"**{mod_name}**")
                temp_lines.extend(mod_lines)
                temp_lines.append("")
        if temp_lines:
            message_lines.append(f"__**{label}:**__")
            message_lines.extend(temp_lines)

    if not any_found:
        await interaction.followup.send("There are no mods currently.")
    else:
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        message_lines.append(f"*Last Update: {timestamp}*")
        await interaction.followup.send("\n".join(message_lines))

keep_alive()

client.run(TOKEN)
