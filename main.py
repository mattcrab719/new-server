import discord
from discord import app_commands, ui
from discord.ext import commands
import asyncio
import io
import requests
import os
import json
from PIL import Image

# --- CONFIGURATION ---
TOKEN = os.getenv('DISCORD_TOKEN')
WELCOME_CH_ID = 1479911571865206804
RULES_CH_ID = 1479912156811231233
BATTLE_CH_ID = 1479914097285005363
LEADERBOARD_CH_ID = 1479923157249822891
RATING_SUBMIT_CH = 1479924175329169458
RATING_VOTE_CH = 1479924157809557689
BATTLE_ROLE_ID = 1479922753225232515
RATER_ROLE_ID = 1479924491000877287

# Role Mappings
MALE_ROLES = {
    "LTN": 1479923820793041130, 
    "MTN": 1479923847569608795, 
    "HTN": 1479923874954215505, 
    "CHADLITE": 1479923900417572874, 
    "CHAD": 1479923892876349661
}
FEMALE_ROLES = {
    "LTB": 1479925354402545898, 
    "MTB": 1479925361977594009, 
    "HTB": 1479925365815119954, 
    "STACYLITE": 1479925369057312818, 
    "STACY": 1479925371439681699
}

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.battle_queue = []
        self.scores = self.load_scores()

    def load_scores(self):
        try:
            with open('scores.json', 'r') as f:
                return json.load(f)
        except:
            return {}

    def save_score(self, user_id):
        uid = str(user_id)
        self.scores[uid] = self.scores.get(uid, 0) + 1
        with open('scores.json', 'w') as f:
            json.dump(self.scores, f)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

# --- UTILS ---
def stitch_images(url1, url2):
    img1 = Image.open(requests.get(url1, stream=True).raw)
    img2 = Image.open(requests.get(url2, stream=True).raw)
    h = 600
    img1 = img1.resize((int(img1.width * h / img1.height), h))
    img2 = img2.resize((int(img2.width * h / img2.height), h))
    new_img = Image.new('RGB', (img1.width + img2.width + 20, h), (43, 45, 49))
    new_img.paste(img1, (0, 0))
    new_img.paste(img2, (img1.width + 20, 0))
    img_byte_arr = io.BytesIO()
    new_img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

# --- COMMANDS ---
@bot.tree.command(name="send", description="Admin: Send a cool announcement")
@app_commands.checks.has_permissions(administrator=True)
async def send_cmd(interaction: discord.Interaction, message: str, title: str = "Announcement", image: discord.Attachment = None):
    embed = discord.Embed(title=title, description=message, color=0x00ffff)
    if image:
        embed.set_image(url=image.url)
    embed.set_footer(text="Official Community Update")
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("Sent!", ephemeral=True)

@bot.tree.command(name="rules", description="Admin: Post rules to the rules channel")
@app_commands.checks.has_permissions(administrator=True)
async def rules_cmd(interaction: discord.Interaction, text: str):
    channel = bot.get_channel(RULES_CH_ID)
    embed = discord.Embed(title="📜 Server Rules", description=text, color=0xff0000)
    await channel.send(embed=embed)
    await interaction.response.send_message("Rules posted!", ephemeral=True)

@bot.tree.command(name="mogbattle", description="Queue for a 1v1 battle")
async def mogbattle(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(ephemeral=True)
    bot.battle_queue.append({"user": interaction.user, "url": image.url})
    
    if len(bot.battle_queue) >= 2:
        p1, p2 = bot.battle_queue.pop(0), bot.battle_queue.pop(0)
        stitched = stitch_images(p1['url'], p2['url'])
        channel = bot.get_channel(BATTLE_CH_ID)
        file = discord.File(stitched, filename="mog.png")
        embed = discord.Embed(title="⚔️ 1v1 MOG BATTLE", description=f"**LEFT:** {p1['user'].mention}\n**RIGHT:** {p2['user'].mention}", color=0x2b2d31)
        embed.set_image(url="attachment://mog.png")
        msg = await channel.send(content=f"<@&{BATTLE_ROLE_ID}>", file=file, embed=embed)
        await msg.add_reaction("⬅️")
        await msg.add_reaction("➡️")
        await interaction.followup.send("Battle is live!")
        
        await asyncio.sleep(10800) # 3 Hours
        msg = await channel.fetch_message(msg.id)
        l_votes = next((r.count for r in msg.reactions if str(r.emoji) == "⬅️"), 1) - 1
        r_votes = next((r.count for r in msg.reactions if str(r.emoji) == "➡️"), 1) - 1
        
        winner = p1['user'] if l_votes > r_votes else p2['user']
        bot.save_score(winner.id)
        await update_lb()
    else:
        await interaction.followup.send("Queued! Waiting for one more...")

async def update_lb():
    channel = bot.get_channel(LEADERBOARD_CH_ID)
    sorted_scores = sorted(bot.scores.items(), key=lambda x: x[1], reverse=True)[:10]
    lb_text = "\n".join([f"**#{i+1}** <@{uid}>: {pts} wins" for i, (uid, pts) in enumerate(sorted_scores)])
    embed = discord.Embed(title="🏆 Mog Battle Leaderboard", description=lb_text or "No wins yet!", color=0xffd700)
    await channel.purge(limit=5)
    await channel.send(embed=embed)

@bot.tree.command(name="ratingmale")
async def ratingmale(interaction: discord.Interaction, img1: discord.Attachment, img2: discord.Attachment = None, img3: discord.Attachment = None):
    await start_rating(interaction, img1, img2, img3, "Male", MALE_ROLES)

@bot.tree.command(name="ratingfemale")
async def ratingfemale(interaction: discord.Interaction, img1: discord.Attachment, img2: discord.Attachment = None, img3: discord.Attachment = None):
    await start_rating(interaction, img1, img2, img3, "Female", FEMALE_ROLES)

async def start_rating(interaction, img1, img2, img3, gender, role_map):
    if interaction.channel_id != RATING_SUBMIT_CH:
        await interaction.response.send_message("Incorrect channel.", ephemeral=True)
        return

    vote_ch = bot.get_channel(RATING_VOTE_CH)

    class RatingView(ui.View):
        def __init__(self):
            super().__init__(timeout=14400)
            self.results = {name: 0 for name in role_map.keys()}
            self.voted_users = set()

        async def handle_click(self, inter: discord.Interaction, name: str):
            if inter.user.id in self.voted_users:
                await inter.response.send_message("You have already voted on this rating!", ephemeral=True)
                return
            self.voted_users.add(inter.user.id)
            self.results[name] += 1
            await inter.response.send_message(f"Voted {name}!", ephemeral=True)

    view = RatingView()

    # Loop through roles and create buttons
    for name in role_map.keys():
        btn = ui.Button(label=name, style=discord.ButtonStyle.blurple)
        
        # We use a helper function or default argument to capture 'name' correctly in the loop
        async def callback_wrapper(inter, n=name):
            await view.handle_click(inter, n)
            
        btn.callback = callback_wrapper
        view.add_item(btn)

    embed = discord.Embed(title=f"{gender} Rating Request", description=f"Submitter: {interaction.user.mention}", color=0x7289da)
    embed.set_image(url=img1.url)
    
    await vote_ch.send(content=f"<@&{RATER_ROLE_ID}>", embed=embed, view=view)
    await interaction.response.send_message("Photo sent for rating!", ephemeral=True)

    # Wait for the duration of the view timeout
    await asyncio.sleep(14400) 

    # Calculate results after 4 hours
    if any(view.results.values()):
        top_role_name = max(view.results, key=view.results.get)
        role_id = role_map[top_role_name]
        role = interaction.guild.get_role(role_id)
        
        if role:
            try:
                await interaction.user.add_roles(role)
                await vote_ch.send(f"✅ {interaction.user.mention} has been rated as **{top_role_name}**.")
            except discord.Forbidden:
                await vote_ch.send(f"❌ Could not assign role to {interaction.user.mention}. Check bot permissions.")
    else:
        await vote_ch.send(f"⚠️ No votes were cast for {interaction.user.mention}'s rating.")

@bot.event
async def on_member_join(member):
    ch = bot.get_channel(WELCOME_CH_ID)
    if ch:
        embed = discord.Embed(title="Welcome!", description=f"Hello {member.mention}! Check <#{RULES_CH_ID}>", color=0x00ff00)
        await ch.send(content=member.mention, embed=embed)

bot.run(TOKEN)
