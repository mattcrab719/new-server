import discord
from discord import app_commands, ui
from discord.ext import commands
import asyncio
import io
import requests
from PIL import Image

# --- CONFIGURATION ---
TOKEN = 'YOUR_BOT_TOKEN_HERE'
WELCOME_CH_ID = 1479911571865206804
RULES_CH_ID = 1479912156811231233
BATTLE_CH_ID = 1479914097285005363
LEADERBOARD_CH_ID = 1479923157249822891
RATING_SUBMIT_CH = 1479924175329169458
RATING_VOTE_CH = 1479924157809557689
BATTLE_ROLE_ID = 1479922753225232515
RATER_ROLE_ID = 1479924491000877287

# Role Mappings
MALE_ROLES = {"LTN": 1479923820793041130, "MTN": 1479923847569608795, "HTN": 1479923874954215505, "CHADLITE": 1479923900417572874, "CHAD": 1479923892876349661}
FEMALE_ROLES = {"LTB": 1479925354402545898, "MTB": 1479925361977594009, "HTB": 1479925365815119954, "STACYLITE": 1479925369057312818, "STACY": 1479925371439681699}

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.battle_queue = []

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

# --- WELCOME SYSTEM ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CH_ID)
    if channel:
        embed = discord.Embed(
            title="Welcome to our Community",
            description=f"Greetings {member.mention}!\n\nWelcome to our looksmaxxing community. We focus on self-improvement and aesthetics. Please ensure you read our guidelines in <#{RULES_CH_ID}> to get started.",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(content=member.mention, embed=embed)

# --- SLASH COMMANDS ---

@bot.tree.command(name="send", description="Admin only: Send a custom embed")
@app_commands.checks.has_permissions(administrator=True)
async def send_msg(interaction: discord.Interaction, title: str, description: str, image_url: str = None):
    embed = discord.Embed(title=title, description=description, color=discord.Color.gold())
    if image_url: embed.set_image(url=image_url)
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("Sent!", ephemeral=True)

@bot.tree.command(name="rules", description="Admin only: Post/Edit Rules")
@app_commands.checks.has_permissions(administrator=True)
async def rules_msg(interaction: discord.Interaction, title: str, rules_text: str):
    channel = bot.get_channel(RULES_CH_ID)
    embed = discord.Embed(title=title, description=rules_text, color=discord.Color.dark_red())
    await channel.send(embed=embed)
    await interaction.response.send_message("Rules updated.", ephemeral=True)

# --- MOG BATTLE SYSTEM ---
def stitch_images(url1, url2):
    img1 = Image.open(requests.get(url1, stream=True).raw)
    img2 = Image.open(requests.get(url2, stream=True).raw)
    # Resize to match height
    h = 500
    img1 = img1.resize((int(img1.width * h / img1.height), h))
    img2 = img2.resize((int(img2.width * h / img2.height), h))
    new_img = Image.new('RGB', (img1.width + img2.width + 10, h), (0, 0, 0))
    new_img.paste(img1, (0, 0))
    new_img.paste(img2, (img1.width + 10, 0))
    img_byte_arr = io.BytesIO()
    new_img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

@bot.tree.command(name="mogbattle", description="Upload an image to queue for a 1v1 battle")
async def mogbattle(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(ephemeral=True)
    bot.battle_queue.append({"user": interaction.user, "url": image.url})
    
    if len(bot.battle_queue) >= 2:
        p1 = bot.battle_queue.pop(0)
        p2 = bot.battle_queue.pop(0)
        stitched = stitch_images(p1['url'], p2['url'])
        
        channel = bot.get_channel(BATTLE_CH_ID)
        file = discord.File(stitched, filename="battle.png")
        embed = discord.Embed(title="⚔️ 1v1 MOG BATTLE", description=f"Left: {p1['user'].mention}\nRight: {p2['user'].mention}", color=0x2b2d31)
        embed.set_image(url="attachment://battle.png")
        
        msg = await channel.send(content=f"<@&{BATTLE_ROLE_ID}>", file=file, embed=embed)
        await msg.add_reaction("⬅️")
        await msg.add_reaction("➡️")
        
        await interaction.followup.send("Battle started in the battle channel!")
        # Timer and leaderboard logic would go here
    else:
        await interaction.followup.send("You are in the queue. Waiting for an opponent...")

# --- RATING SYSTEM ---
class RatingView(ui.View):
    def __init__(self, gender, member_id):
        super().__init__(timeout=14400) # 4 hours
        self.gender = gender
        self.member_id = member_id
        self.votes = {k: 0 for k in (MALE_ROLES.keys() if gender == "male" else FEMALE_ROLES.keys())}

    async def add_vote(self, interaction, label):
        self.votes[label] += 1
        await interaction.response.send_message(f"Voted for {label}!", ephemeral=True)

# Note: Full rating logic with role assignment requires a persistent listener 
# and a background task for the 4-hour timer.

@bot.tree.command(name="ratingmale", description="Submit photos for a male rating")
async def ratingmale(interaction: discord.Interaction, img1: discord.Attachment, img2: discord.Attachment = None, img3: discord.Attachment = None):
    if interaction.channel_id != RATING_SUBMIT_CH: return
    channel = bot.get_channel(RATING_VOTE_CH)
    embed = discord.Embed(title="Male Rating Request", description=f"User: {interaction.user.mention}", color=discord.Color.blue())
    embed.set_image(url=img1.url)
    
    view = ui.View()
    for label in MALE_ROLES.keys():
        btn = ui.Button(label=label, style=discord.ButtonStyle.grey)
        view.add_item(btn)
        
    await channel.send(content=f"<@&{RATER_ROLE_ID}>", embed=embed, view=view)
    await interaction.response.send_message("Submitted for rating!", ephemeral=True)

bot.run(TOKEN)
