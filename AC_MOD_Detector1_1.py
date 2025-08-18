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

subprocess.Popen(["python", "Account_Detector1_1.py"])

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

    async def build_known_mod_status(self) -> str:
        KNOWN_MODS, UNKNOWN_MODS = get_mods_db()
        ALL_MODS = list({uid for mod_name, ids in KNOWN_MODS + UNKNOWN_MODS for uid in ids})

        async with aiohttp.ClientSession() as session:
            async with session.post("https://presence.roblox.com/v1/presence/users", json={"userIds": ALL_MODS}) as resp:
                if resp.status != 200:
                    return "Error obtaining presence."
                data = await resp.json()

            presences = data.get("userPresences", [])
            presence_dict = {user["userId"]: user["userPresenceType"] for user in presences}

            message_lines = []
            any_in_game = False

            message_lines.append("__**Known Mods:**__")
            for mod_name, user_ids in KNOWN_MODS:
                message_lines.append(f"**{mod_name}**")
                for uid in user_ids:
                    async with session.get(f"https://users.roblox.com/v1/users/{uid}") as user_resp:
                        if user_resp.status == 200:
                            user_data = await user_resp.json()
                            username = user_data.get("name", "Unknown")
                        else:
                            username = "Unknown"

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

    async def build_unknown_mod_status(self) -> str:
        KNOWN_MODS, UNKNOWN_MODS = get_mods_db()
        ALL_MODS = list({uid for mod_name, ids in KNOWN_MODS + UNKNOWN_MODS for uid in ids})

        async with aiohttp.ClientSession() as session:
            async with session.post("https://presence.roblox.com/v1/presence/users", json={"userIds": ALL_MODS}) as resp:
                if resp.status != 200:
                    return "Error obtaining presence."
                data = await resp.json()

            presences = data.get("userPresences", [])
            presence_dict = {user["userId"]: user["userPresenceType"] for user in presences}

            message_lines = []
            any_in_game = False

            message_lines.append("__**Unknown Mods:**__")
            for mod_name, user_ids in UNKNOWN_MODS.items():
                message_lines.append(f"**{mod_name}**")
                for uid in user_ids:
                    async with session.get(f"https://users.roblox.com/v1/users/{uid}") as user_resp:
                        if user_resp.status == 200:
                            user_data = await user_resp.json()
                            username = user_data.get("name", "Unknown")
                        else:
                            username = "Unknown"

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

client = MyClient()

@client.tree.command(name="mods", description="Shows if a known mod is online")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def mods(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    content = await client.build_known_mod_status()
    await interaction.followup.send(content)

@client.tree.command(name="unknownmods", description="Shows if an unknown mod is online")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def unknownmods(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    content = await client.build_unknown_mod_status()
    await interaction.followup.send(content)

@client.tree.command(name="checkmods", description="Checks known mods every minute")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def checkmods(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    message = await interaction.followup.send("Started checking...")

    async def periodic_check(msg):
        current_msg = msg
        while True:
            try:
                content = await client.build_known_mod_status()
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
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def modson(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    KNOWN_MODS, UNKNOWN_MODS = get_mods_db()
    ALL_MODS = list({uid for mod_name, ids in KNOWN_MODS + UNKNOWN_MODS for uid in ids})
    valid_user_ids = [uid for uid in ALL_MODS if uid > 0]

    BATCH_SIZE = 50
    presence_dict = {}
    message_lines = []

    async with aiohttp.ClientSession() as session:
        for i in range(0, len(valid_user_ids), BATCH_SIZE):
            batch = valid_user_ids[i:i+BATCH_SIZE]
            print(f"[modson] Sending batch: {batch}")

            try:
                async with session.post(
                    "https://presence.roblox.com/v1/presence/users",
                    json={"userIds": batch}
                ) as resp:
                    print(f"[modson] Response status: {resp.status}")
                    if resp.status != 200:
                        continue
                    data = await resp.json()
                    for user in data.get("userPresences", []):
                        presence_dict[int(user["userId"])] = user
            except Exception as e:
                print(f"[modson] Error fetching batch: {e}")

        any_found = False

        async def process_mod_list(mod_list, label):
            nonlocal any_found
            result_lines = []
            temp_lines = []

            for mod_name, user_ids in mod_list:
                mod_lines = []
                for uid in user_ids:
                    uid_int = int(uid)
                    presence_info = presence_dict.get(uid_int)
                    if presence_info and presence_info["userPresenceType"] in [1, 2]:
                        try:
                            async with session.get(f"https://users.roblox.com/v1/users/{uid_int}") as user_resp:
                                if user_resp.status == 200:
                                    user_data = await user_resp.json()
                                    username = user_data.get("name", "Unknown")
                                else:
                                    username = "Unknown"
                        except:
                            username = "Unknown"

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
                result_lines.append(f"__**{label}:**__")
                result_lines.extend(temp_lines)

            return result_lines

        message_lines += await process_mod_list(KNOWN_MODS, "Known Mods")
        message_lines += await process_mod_list(UNKNOWN_MODS, "Unknown Mods")

    if not any_found:
        await interaction.followup.send("There are no mods currently.")
    else:
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        message_lines.append(f"*Last Update: {timestamp}*")
        await interaction.followup.send("\n".join(message_lines))

keep_alive()


client.run(TOKEN)
