import datetime
import json
import os
import time
from typing import Optional

import discord
from discord import Option
from discord.ext import commands, tasks
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load bot token
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Load server IDs
SERVERS = [1170901789902639193, 1084252257777889280]

# Load user IDs
SELINA_ID = 644277562461257730
VIVIAN_ID = 5925034051220275203

# Create bot
bot = discord.Bot()
bot.owner_ids = [SELINA_ID, VIVIAN_ID]


@bot.command(guild_ids=SERVERS, description='Sends the bot\'s latency.') # this decorator makes a slash command
async def ping(ctx):
    '''Returns the bot's latency.'''
    await ctx.respond(f'Pong! Latency is {int(1000 * bot.latency)}ms.')

@commands.is_owner()
@bot.command(guild_ids=SERVERS)
async def create_flashbang_role(ctx):
    guild = ctx.guild

    bot_top_role = ctx.me.top_role

    role = discord.utils.get(guild.roles, name='Flashbang') 
    if role is None:
        role = await guild.create_role(name="Flashbang")
    if role.position > bot_top_role.position:
        await ctx.respond('The flashbang role is above the bot\'s top role. Please move the flashbang role below the bot\'s top role.')
        return
    if role.position < ctx.author.top_role.position:
        await role.edit(position=bot_top_role.position - 1)
    
    for channel in guild.channels:
        await channel.set_permissions(role, read_messages=False, send_messages=False)

    await ctx.respond('The flashbang role has been created.')

@bot.command(guild_ids=SERVERS, description='Flashbangs the user for the specified amount of time, in seconds.')
async def flashbang(ctx, time: Option(int)):
    guild = ctx.guild
    unix_timestamp = datetime.datetime.now(datetime.timezone.utc).timestamp()
    flasbang_role = discord.utils.get(guild.roles, name='Flashbang')

    if flasbang_role is None:
        await ctx.respond('The flashbang role does not exist. Please have the server owner create the flashbang role using the `/create_flashbang_role` command.')
        return

    if ctx.author.top_role.position > ctx.me.top_role.position:
        await ctx.respond('You are above the bot\'s top role. Please move yourself below the bot\'s top role in order to flashbang yourself.')
        return

    admin_roles = []
    for role in ctx.author.roles:
        if role.permissions.administrator:
            if role == ctx.guild.default_role:
                await ctx.respond('The default role cannot be an admin.')
                return
            admin_roles.append(role.id)

    confirmation_message = f"Are you sure you want to flashbang yourself for {time} seconds?"
    confirmed = await confirm(ctx, confirmation_message)

    if confirmed:
        with open('flashbangs.json', 'r', encoding='utf-8') as f:
            flashbangs = json.load(f)

        flashbangs[ctx.author.id] = {'Time': unix_timestamp + time, 'Guild': guild.id, 'Admins': admin_roles}

        with open('flashbangs.json', 'w', encoding='utf-8') as f:
            json.dump(flashbangs, f)

        await ctx.author.add_roles(flasbang_role)
        await ctx.respond('Flashbanged!', ephemeral=True)
    else:
        await ctx.respond('Flashbang canceled.', ephemeral=True)

async def confirm(ctx: discord.Interaction, text: str) -> Optional[bool]:
    class ConfirmationView(discord.ui.View):
        def __init__(self, ctx: discord.Interaction, text: str):
            super().__init__(timeout=60)
            self.ctx = ctx
            self.text = text
            self.value = None

        @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
        async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.value = True
            await interaction.response.send_message("Confirmed", ephemeral=True)
            self.stop()

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
        async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
            self.value = False
            await interaction.response.send_message("Canceled", ephemeral=True)
            self.stop()

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user != self.ctx.user:
                await interaction.response.send_message("This confirmation panel is not for you.", ephemeral=True)
                return False
            return True

    view = ConfirmationView(ctx, text)
    await ctx.response.send_message(text, view=view, ephemeral=True)
    await view.wait()
    return view.value

async def check_flashbangs(bot):
    current_time = time.time()
    with open('flashbangs.json', 'r') as f:
        flashbangs = json.load(f)

    for member_id, flashbang_data in flashbangs.copy().items():
        guild_id = int(flashbang_data['Guild'])
        guild = bot.get_guild(guild_id)
        if guild is None:
            continue

        member = guild.get_member(int(member_id))
        if member is None:
            continue

        flashbang_role = discord.utils.get(guild.roles, name='Flashbang')
        if flashbang_role is None:
            continue

        if flashbang_data['Time'] <= current_time:
            for admin_role_id in flashbang_data['Admins']:
                admin_role = discord.utils.get(guild.roles, id=admin_role_id)
                if admin_role is not None:
                    member.add_roles(admin_role)
            await member.remove_roles(flashbang_role)
            del flashbangs[member_id]

    with open('flashbangs.json', 'w') as f:
        json.dump(flashbangs, f)

@tasks.loop(seconds=5)
async def check_flashbangs_task():
    await bot.wait_until_ready()
    await check_flashbangs(bot)

@bot.event
async def on_ready():
    check_flashbangs_task.start()
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

bot.run(DISCORD_BOT_TOKEN)