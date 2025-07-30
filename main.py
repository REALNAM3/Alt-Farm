import discord
from discord import app_commands
import aiohttp
import asyncio
import datetime
import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Alt farm"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

PRESENCE_TYPES = {
    0: "Offline",
    1: "Online",
    2: "In Game",
    3: "In Studio",
}

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
    "Sponge": [376388734, 5157136850],
    "Gora": [589533315],
}

UNKNOWN_MODS = {
    "NNs": [
        7547477786, 7574577126, 2043525911, 5816563976, 240526951, 7587479685,
        1160595313, 7876617827, 7693766866, 2568824396, 7604102307, 7901878324,
        5087196317, 7187604802, 7495829767, 7718511355, 7928472983, 7922414080,
        7758683476
    ]
}


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
        all_user_ids = list({uid for ids in ALL_MODS.values() for uid in ids})

        async with aiohttp.ClientSession() as session:
            async with session.post("https://presence.roblox.com/v1/presence/users", json={"userIds": all_user_ids}) as resp:
                if resp.status != 200:
                    return "Error obtaining presence."
                data = await resp.json()

            presences = data.get("userPresences", [])
            presence_dict = {user["userId"]: user["userPresenceType"] for user in presences}

            message_lines = []
            any_in_game = False

            message_lines.append("__**Known Mods:**__")
            for mod_name, user_ids in ALL_MODS.items():
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
        all_user_ids = list({uid for ids in UNKNOWN_MODS.values() for uid in ids})

        async with aiohttp.ClientSession() as session:
            async with session.post("https://presence.roblox.com/v1/presence/users", json={"userIds": all_user_ids}) as resp:
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
async def mods(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    content = await client.build_known_mod_status()
    await interaction.followup.send(content)


@client.tree.command(name="unknownmods", description="Shows if an unknown mod is online")
async def unknownmods(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    content = await client.build_unknown_mod_status()
    await interaction.followup.send(content)


@client.tree.command(name="checkmods", description="Checks known mods every minute")
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


@client.tree.command(name="stopcheck", description="Stops the check from the command /checkmods")
async def stopcheck(interaction: discord.Interaction):
    await interaction.response.defer()
    if client.checking_task and not client.checking_task.done():
        client.checking_task.cancel()
        await interaction.followup.send("Stopped checking.")
    else:
        await interaction.followup.send("No current check running.")


@client.tree.command(name="modson", description="Checks if any mod (known or unknown) is in game")
async def modson(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    all_user_ids = list({uid for ids in list(ALL_MODS.values()) + list(UNKNOWN_MODS.values()) for uid in ids})
    message_lines = []

    async with aiohttp.ClientSession() as session:
        async with session.post("https://presence.roblox.com/v1/presence/users", json={"userIds": all_user_ids}) as resp:
            if resp.status != 200:
                await interaction.followup.send("Error obtaining presence.")
                return
            data = await resp.json()

        presences = data.get("userPresences", [])
        presence_dict = {user["userId"]: user for user in presences}

        any_found = False

        async def process_mod_list(mod_list, label):
            nonlocal any_found
            result_lines = [f"__**{label}:**__"]
            for mod_name, user_ids in mod_list.items():
                mod_lines = []
                for uid in user_ids:
                    presence_info = presence_dict.get(uid)
                    if presence_info and presence_info["userPresenceType"] in [1, 2]:
                        async with session.get(f"https://users.roblox.com/v1/users/{uid}") as user_resp:
                            if user_resp.status == 200:
                                user_data = await user_resp.json()
                                username = user_data.get("name", "Unknown")
                            else:
                                username = "Unknown"
                        if presence_info["userPresenceType"] == 2:
                            mod_lines.append(f"```diff\n+[In Game]: {username} \n```")
                        else:
                            mod_lines.append(f"```ini\n[Online]: {username}\n```")
                        any_found = True
                if mod_lines:
                    result_lines.append(f"**{mod_name}**")
                    result_lines.extend(mod_lines)
                    result_lines.append("")
            return result_lines

        message_lines += await process_mod_list(ALL_MODS, "Known Mods")
        message_lines += await process_mod_list(UNKNOWN_MODS, "Unknown Mods")

    if not any_found:
        await interaction.followup.send("There are no mods currently.")
    else:
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        message_lines.append(f"*Last Update: {timestamp}*")
        await interaction.followup.send("\n".join(message_lines))

keep_alive()

client.run(os.getenv("BOT_TOKEN"))
