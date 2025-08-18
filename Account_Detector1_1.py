import discord
import ssl
import aiohttp
import os
from dotenv import load_dotenv
from discord import app_commands
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN2")
ROBLOSECURITY = os.getenv("ROBLOXSECURITY")
MONGO_URI = os.getenv("MONGO_URI")

cluster = MongoClient(MONGO_URI, server_api=ServerApi('1'), tls=True, tlsAllowInvalidCertificates=False, ssl_cert_reqs=ssl.CERT_REQUIRED)
db = cluster["bot_detector"]
groups = db["groups"]

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        await self.tree.sync()
        print(f"Bot connected as {self.user} ({self.user.id})")

client = MyClient()

async def get_user_info(session, username: str):
    try:
        async with session.post(
            "https://users.roblox.com/v1/usernames/users",
            json={"usernames": [username], "excludeBannedUsers": False}
        ) as resp:
            user_data = await resp.json()
    except Exception as e:
        return None, f"Error fetching user: {e}"

    if "data" not in user_data or len(user_data["data"]) == 0:
        return None, f"User `{username}` not found"

    user_id = user_data["data"][0]["id"]
    display_name = user_data["data"][0].get("displayName", username)

    try:
        async with session.post(
            "https://presence.roblox.com/v1/presence/users",
            json={"userIds": [user_id]}
        ) as resp:
            presence = await resp.json()
    except Exception as e:
        return None, f"Error fetching presence: {e}"

    if "userPresences" not in presence or len(presence["userPresences"]) == 0:
        return None, f"No presence data for `{username}`"

    user_presence = presence["userPresences"][0]

    avatar_url = None
    try:
        async with session.get(
            f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=720x720&format=Png&isCircular=true"
        ) as avatar_resp:
            avatar_data = await avatar_resp.json()
            if "data" in avatar_data and len(avatar_data["data"]) > 0:
                avatar_url = avatar_data["data"][0].get("imageUrl")
    except:
        pass

    place_id = user_presence.get("placeId", "Unknown")
    job_id = user_presence.get("gameId", "Unknown")
    game_name = "Unknown"

    universe_id = user_presence.get("universeId")
    if universe_id:
        try:
            async with session.get(f"https://games.roblox.com/v1/games?universeIds={universe_id}") as game_resp:
                game_info = await game_resp.json()
                if "data" in game_info and len(game_info["data"]) > 0:
                    game_name = game_info["data"][0].get("name", "Unknown")
        except:
            pass

    presence_type = user_presence.get("userPresenceType", 0)
    if presence_type == 1:
        embed = discord.Embed(title=f"{display_name} (@{username}) is online", color=discord.Color.blue())
    elif presence_type == 2:
        embed = discord.Embed(
            title=f"{display_name} (@{username}) is playing",
            description=f"Game: `{game_name}`\nPlaceId: `{place_id}`\nJobId: `{job_id}`",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(title=f"{display_name} (@{username}) is offline", color=discord.Color.red())

    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    return embed, None

@client.tree.command(name="group", description="Insert group name and main names or alt names")
@app_commands.describe(group_name="Enter the group name")
@app_commands.describe(mains="Enter the mains names separated by commas")
@app_commands.describe(alts="Enter the alts names separated by commas (or type none)")
async def group(interaction: discord.Interaction, group_name: str, mains: str, alts: str = "none"):
    mains_list = [m.strip() for m in mains.split(",") if m.strip()]
    alts_list = [] if alts.lower() == "none" else [a.strip() for a in alts.split(",") if a.strip()]

    groups.update_one(
        {"group_name": group_name},
        {"$set": {"mains": mains_list, "alts": alts_list}},
        upsert=True
    )

    embed = discord.Embed(
        title=f" Group `{group_name}` saved",
        description=f"**Mains:** {', '.join(mains_list) if mains_list else 'None'}\n**Alts:** {', '.join(alts_list) if alts_list else 'None'}",
        color=discord.Color.dark_gray()
    )
    await interaction.response.send_message(embed=embed)

@client.tree.command(name="snipe", description="Watch user status and JobId")
@app_commands.describe(username="Enter the username")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def snipe(interaction: discord.Interaction, username: str):
    await interaction.response.defer()

    async with aiohttp.ClientSession(cookies={".ROBLOSECURITY": ROBLOSECURITY}) as session:
        embed, error = await get_user_info(session, username)
        if error:
            await interaction.followup.send(error)
        else:
            await interaction.followup.send(embed=embed)

@client.tree.command(name="snipegroup", description="Get group info and status by group name")
@app_commands.describe(group_name="Enter the group name")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def snipegroup(interaction: discord.Interaction, group_name: str):
    await interaction.response.defer()

    group_data = groups.find_one({"group_name": group_name})
    if not group_data:
        await interaction.followup.send(f" Group `{group_name}` not found")
        return

    mains = group_data.get("mains", [])
    alts = group_data.get("alts", [])

    if not mains and not alts:
        await interaction.followup.send(f"Group `{group_name}` has no members saved")
        return

    group_embed = discord.Embed(
        title=f" Group: {group_name}",
        description=f"Checking : {len(mains) + len(alts)} users...",
        color=discord.Color.dark_gray()
    )
    await interaction.followup.send(embed=group_embed)

    async with aiohttp.ClientSession(cookies={".ROBLOSECURITY": ROBLOSECURITY}) as session:
        for user in mains + alts:
            embed, error = await get_user_info(session, user)
            if error:
                await interaction.channel.send(error)
            else:
                await interaction.channel.send(embed=embed)

client.run(TOKEN)


