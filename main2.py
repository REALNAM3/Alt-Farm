import discord
import requests
from discord import app_commands
import os

TOKEN = os.getenv("BOT_TOKEN2")
ROBLOSECURITY = os.getenv("ROBLOXSECURITY")

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        await self.tree.sync()
        print(f"Bot connected as {self.user}")

client = MyClient()

@client.tree.command(name="snipe", description="Watch user status and JobId")
@app_commands.describe(username="Enter the username")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def snipe(interaction: discord.Interaction, username: str):
    await interaction.response.defer()

    user_url = "https://users.roblox.com/v1/usernames/users"
    data = {"usernames": [username], "excludeBannedUsers": False}
    try:
        response = requests.post(user_url, json=data, timeout=5)
        user_data = response.json()
    except Exception as e:
        await interaction.followup.send(f"Unknown user: {e}")
        return

    if "data" not in user_data or len(user_data["data"]) == 0:
        await interaction.followup.send("User not found")
        return

    user_id = user_data["data"][0]["id"]
    display_name = user_data["data"][0].get("displayName", username)

    presence_url = "https://presence.roblox.com/v1/presence/users"
    headers = {"Content-Type": "application/json"}
    payload = {"userIds": [user_id]}
    cookies = {".ROBLOSECURITY": ROBLOSECURITY}
    presence = requests.post(presence_url, json=payload, headers=headers, cookies=cookies).json()

    user_presence = presence["userPresences"][0]

    avatar_api_url = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=720x720&format=Png&isCircular=true"
    avatar_response = requests.get(avatar_api_url).json()
    avatar_url = None
    if "data" in avatar_response and len(avatar_response["data"]) > 0:
        avatar_url = avatar_response["data"][0].get("imageUrl")

    place_id = user_presence.get("placeId", "Unknown")
    job_id = user_presence.get("gameId", "Unknown")
    game_name = "Unknown"
    
    universe_id = user_presence.get("universeId")
    if universe_id:
        game_info_url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
        game_info = requests.get(game_info_url).json()
        if "data" in game_info and len(game_info["data"]) > 0:
            game_name = game_info["data"][0].get("name", "Unknown")
    
    if user_presence["userPresenceType"] == 1:
        embed = discord.Embed(
            title=f"{display_name}(@{username}) is online",
            color=discord.Color.blue()
        )
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        await interaction.followup.send(embed=embed, ephemeral=False)
        return
    
    elif user_presence["userPresenceType"] == 2:
        embed = discord.Embed(
            title=f"{display_name}(@{username}) is playing",
            description=f"Game: `{game_name}`\nPlaceId: `{place_id}`\nJobId: `{job_id}`",
            color=discord.Color.green()
        )
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        await interaction.followup.send(embed=embed, ephemeral=False)
        return

    elif user_presence["userPresenceType"] == 3:
        embed = discord.Embed(
            title=f"{display_name}(@{username}) is offline",
            color=discord.Color.red()
        )
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        await interaction.followup.send(embed=embed, ephemeral=False)
        return

client.run(TOKEN)
