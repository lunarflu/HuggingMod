import discord
import os
import threading
import gradio as gr
import requests
import json
import random
import time
import re
from discord import Embed, Color
from discord.ext import commands
from gradio_client import Client
from PIL import Image
from ratelimiter import RateLimiter
from datetime import datetime # for times
from pytz import timezone # for times
import asyncio # check if used

zurich_tz = timezone("Europe/Zurich")

def convert_to_timezone(dt, tz):
    return dt.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S %Z")

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", None)
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
testclient = Client("https://lunarflu-bert-test.hf.space/--replicas/58fjw/")

#rate_limiter = RateLimiter(max_calls=10, period=60)  # needs testing

# stats stuff ---------------------------------------------------------------------------------------------------------------------------------------------------------
number_of_messages = 0
user_cooldowns = {}

@bot.event
async def on_message(message):
    try:  
        global number_of_messages
        if message.author != bot.user:
            lunarflu = bot.get_user(811235357663297546) #811235357663297546
            cakiki = bot.get_user(416019758492680203)
            
            """Backup"""
            number_of_messages = number_of_messages + 1
            message_link = f"[#{message.channel.name}]({message.jump_url})"
            msgcnt = message.content
            try:
                job = testclient.submit(msgcnt, api_name="/predict")
                while not job.done():
                    pass
                result = job.result()
                label = result['label']
                print(f"label: {label}")
            except Exception as e:
                print(f"testclient error: {e}")                       
            dm_message = await lunarflu.send(f"{number_of_messages}| {label} |{message_link} |{message.author}: {message.content}")

            """Antispam"""
            #Detecting certain unwanted strings
            try:
                forbidden_strings = ["@everyone", "@here", "discord.gg", "discord.com/invite", "discord.com", "discord-premium"]
                if any(string.lower() in message.content.lower() for string in forbidden_strings):
                    ignored_role_ids = [897381378172264449, 897376942817419265] #admins, huggingfolks
                    if any(role.id in ignored_role_ids for role in message.author.roles):
                        if message.author != lunarflu:
                            return
                    dm_unwanted = await lunarflu.send(f" {lunarflu.mention} [experimental] SUSPICIOUS MESSAGE: {message_link} | {message.author}: {message.content}")
                    dm_unwanted = await cakiki.send(f" {cakiki.mention} [experimental] SUSPICIOUS MESSAGE: {message_link} | {message.author}: {message.content}")
            except Exception as e:
                print(f"Antispam->Detecting certain unwanted strings Error: {e}")

            #Posting too fast
            cooldown_duration = 3  # messages per n seconds, was 1, now 3, could try 5
            if message.author.id not in user_cooldowns:
                user_cooldowns[message.author.id] = {'count': 1, 'timestamp': message.created_at}
            else:
                if (message.created_at - user_cooldowns[message.author.id]['timestamp']).total_seconds() > cooldown_duration:
                    var1 = message.created_at
                    var2 = user_cooldowns[message.author.id]['timestamp']
                    print(f"seconds since last message by {message.author}: ({var1} - {var2}).seconds = {(var1 - var2).total_seconds()}")

                    # if we wait longer than cooldown_duration, count will reset 
                    user_cooldowns[message.author.id] = {'count': 1, 'timestamp': message.created_at}
                else:
                    user_cooldowns[message.author.id]['count'] += 1

                    # tldr; if we post 2 messages with less than 1s between them
                    if user_cooldowns[message.author.id]['count'] > 3: # 4 in a row, helps avoid false positives for posting in threads
                        var1 = message.created_at
                        var2 = user_cooldowns[message.author.id]['timestamp']
                        print(f"seconds since last message by {message.author}: {(var1 - var2).total_seconds()}")   
                        spam_count = user_cooldowns[message.author.id]['count']
                        print(f"count: {user_cooldowns[message.author.id]['count']}")

                        test_server = os.environ.get('TEST_SERVER')
                        if test_server == 'True':
                            alert = "<@&1106995261487710411>" # test @alerts role
                        if test_server == 'False':
                            alert = "<@&1108342563628404747>" # normal @alerts role

                        await bot.log_channel.send(
                            f"[EXPERIMENTAL ALERT] {message.author} may be posting too quickly! \n"
                            f"Spam count: {user_cooldowns[message.author.id]['count']}\n"
                            f"Message content: {message.content}\n"
                            f"[Jump to message!](https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id})\n"
                            f"{alert}"
                        )
                        await cakiki.send(
                            f"[EXPERIMENTAL ALERT] {message.author} may be posting too quickly! \n"
                            f"Spam count: {user_cooldowns[message.author.id]['count']}\n"
                            f"Message content: {message.content}\n"
                            f"[Jump to message!](https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id})\n"
                        )
                    """
                    if user_cooldowns[message.author.id]['count']/5 > cooldown_duration:
                        # ping admins
                        # timeout for user
                        # kick user
                    """    
            user_cooldowns[message.author.id]['timestamp'] = message.created_at  

        await bot.process_commands(message)

    except Exception as e:
        print(f"on_message Error: {e}")     

# moderation stuff-----------------------------------------------------------------------------------------------------------------------------------------------------
        
@bot.event
async def on_message_edit(before, after):
    try:
        if before.author == bot.user:
            return
    
        if before.content != after.content:
            embed = Embed(color=Color.orange())
            embed.set_author(name=f"{before.author}    ID: {before.author.id}", icon_url=before.author.avatar.url if before.author.avatar else bot.user.avatar.url)
            embed.title = "Message Edited"
            embed.description = f"**Before:** {before.content or '*(empty message)*'}\n**After:** {after.content or '*(empty message)*'}"
            embed.add_field(name="Author Username", value=before.author.name, inline=True)
            embed.add_field(name="Channel", value=before.channel.mention, inline=True)
            #embed.add_field(name="Message Created On", value=before.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
            embed.add_field(name="Message Created On", value=convert_to_timezone(before.created_at, zurich_tz), inline=True)
            embed.add_field(name="Message ID", value=before.id, inline=True)
            embed.add_field(name="Message Jump URL", value=f"[Jump to message!](https://discord.com/channels/{before.guild.id}/{before.channel.id}/{before.id})", inline=True)
            if before.attachments:
                attachment_urls = "\n".join([attachment.url for attachment in before.attachments])
                embed.add_field(name="Attachments", value=attachment_urls, inline=False)
            #embed.set_footer(text=f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            embed.set_footer(text=f"{convert_to_timezone(datetime.utcnow(), zurich_tz)}")
            await bot.log_channel.send(embed=embed)
            
    except Exception as e:
        print(f"on_message_edit Error: {e}")        

@bot.event
async def on_message_delete(message):
    try:    
        if message.author == bot.user:
            return
    
        embed = Embed(color=Color.red())
        embed.set_author(name=f"{message.author}    ID: {message.author.id}", icon_url=message.author.avatar.url if message.author.avatar else bot.user.avatar.url)
        embed.title = "Message Deleted"
        embed.description = message.content or "*(empty message)*"
        embed.add_field(name="Author Username", value=message.author.name, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        #embed.add_field(name="Message Created On", value=message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
        embed.add_field(name="Message Created On", value=convert_to_timezone(message.created_at, zurich_tz), inline=True)
        embed.add_field(name="Message ID", value=message.id, inline=True)
        embed.add_field(name="Message Jump URL", value=f"[Jump to message!](https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id})", inline=True)
        if message.attachments:
            attachment_urls = "\n".join([attachment.url for attachment in message.attachments])
            embed.add_field(name="Attachments", value=attachment_urls, inline=False)
        #embed.set_footer(text=f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        embed.set_footer(text=f"{convert_to_timezone(datetime.utcnow(), zurich_tz)}")
        await bot.log_channel.send(embed=embed)
        
    except Exception as e:
        print(f"on_message_delete Error: {e}")  

# nickname stuff ---------------------------------------------------------------------------------------------------------------------------
@bot.event
async def on_member_update(before, after):
    try:    
        """
        if before.name != after.name:
        async for entry in before.guild.audit_logs(limit=5):
            print(f'{entry.user} did {entry.action} to {entry.target}')        
        """
        if before.nick != after.nick:
            embed = Embed(color=Color.orange())
            embed.set_author(name=f"{after}    ID: {after.id}", icon_url=after.avatar.url if after.avatar else bot.user.avatar.url)
            embed.title = "Nickname Modified"
            embed.add_field(name="Mention", value=after.mention, inline=True)
            embed.add_field(name="Old", value=before.nick, inline=True)
            embed.add_field(name="New", value=after.nick, inline=True)
            embed.set_footer(text=f"{convert_to_timezone(datetime.utcnow(), zurich_tz)}")
            await bot.log_channel.send(embed=embed)
            
    except Exception as e:
        print(f"on_member_update Error: {e}")     
        

@bot.event
async def on_member_ban(guild, banned_user):
    try:
        await asyncio.sleep(1)
        entry1 = await guild.fetch_ban(banned_user)
        ban_reason = entry1.reason
        print(f"ban_reason: {ban_reason}")

        async for entry2 in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            if ban_reason:
                print(f'{entry2.user} banned {entry2.target} for {ban_reason}')
            else:
                print(f'{entry2.user} banned {entry2.target} (no reason specified)')             
            
            content = "<@&1108342563628404747>" # @alerts role
            embed = Embed(color=Color.red())
            embed.set_author(name=f"{entry2.target}    ID: {entry2.target.id}", icon_url=entry2.target.avatar.url if entry2.target.avatar else bot.user.avatar.url)
            embed.title = "User Banned"
            embed.add_field(name="User", value=entry2.target.mention, inline=True)
            #nickname = entry2.target.nick if entry2.target.nick else "None"
            #embed.add_field(name="Nickname", value=nicknmae, inline=True)
            #embed.add_field(name="Account Created At", value=entry2.target.created_at, inline=True)
            embed.add_field(name="Moderator", value=entry2.user.mention, inline=True)
            embed.add_field(name="Nickname", value=entry2.user.nick, inline=True)
            embed.add_field(name="Reason", value=ban_reason, inline=False)
            embed.set_footer(text=f"{convert_to_timezone(datetime.utcnow(), zurich_tz)}")

            #user = bot.get_user(811235357663297546)
            #dm_message = await user.send(content=content, embed=embed)
            await bot.log_channel.send(content=content, embed=embed)  

    except Exception as e:
        print(f"on_member_ban Error: {e}")     


@bot.event
async def on_member_unban(guild, unbanned_user):
    try:
        await asyncio.sleep(5)
        async for entry in guild.audit_logs(action=discord.AuditLogAction.unban, limit=1):
            if unbanned_user == entry.target: # verify that unbanned user is in audit log
                moderator = entry.user    

                created_and_age = f"{unbanned_user.created_at}"
                content = "<@&1108342563628404747>" # @alerts role
                embed = Embed(color=Color.red())
                embed.set_author(name=f"{unbanned_user}    ID: {unbanned_user.id}", icon_url=unbanned_user.avatar.url if unbanned_user.avatar else bot.user.avatar.url)
                embed.title = "User Unbanned"
                embed.add_field(name="User", value=unbanned_user.mention, inline=True)
                embed.add_field(name="Account Created At", value=created_and_age, inline=True)
                embed.add_field(name="Moderator", value=moderator.mention, inline=True)
                embed.add_field(name="Nickname", value=moderator.nick, inline=True)
                embed.set_footer(text=f"{convert_to_timezone(datetime.utcnow(), zurich_tz)}")
                
                #user = bot.get_user(811235357663297546)
                #dm_message = await user.send(content=content, embed=embed)
                await bot.log_channel.send(content=content, embed=embed)   
              
    except Exception as e:
        print(f"on_member_unban Error: {e}")  

# admin stuff-----------------------------------------------------------------------------------------------------------------------


@bot.event
async def on_member_join(member):
    try:
        await asyncio.sleep(5)
        embed = Embed(color=Color.blue())
        avatar_url = member.avatar.url if member.avatar else bot.user.avatar.url
        embed.set_author(name=f"{member}    ID: {member.id}", icon_url=avatar_url)
        embed.title = "User Joined"
        embed.add_field(name="Mention", value=member.mention, inline=True)
        embed.add_field(name="Nickname", value=member.nick, inline=True)
        embed.add_field(name="Account Created At", value=member.created_at, inline=True)
        embed.set_footer(text=f"{convert_to_timezone(datetime.utcnow(), zurich_tz)}")
        await bot.log_channel.send(embed=embed)  
        
    except Exception as e:
        print(f"on_member_join Error: {e}")  


@bot.event
async def on_member_remove(member):
    try:
        embed = Embed(color=Color.blue())
        embed.set_author(name=f"{member}    ID: {member.id}", icon_url=member.avatar.url if member.avatar else bot.user.avatar.url)
        embed.title = "User Left"
        embed.add_field(name="Mention", value=member.mention, inline=True)
        embed.add_field(name="Nickname", value=member.nick, inline=True)
        embed.add_field(name="Account Created At", value=member.created_at, inline=True)
        embed.set_footer(text=f"{convert_to_timezone(datetime.utcnow(), zurich_tz)}")
        await bot.log_channel.send(embed=embed)  
        
    except Exception as e:
        print(f"on_member_remove Error: {e}")  


@bot.event
async def on_guild_channel_create(channel):
    try:
        # creating channels
        embed = Embed(description=f'Channel {channel.mention} was created', color=Color.green())
        await bot.log_channel.send(embed=embed)
    except Exception as e:
        print(f"on_guild_channel_create Error: {e}")  

    
@bot.event
async def on_guild_channel_delete(channel):
    try:
        # deleting channels, should ping @alerts for this
        embed = Embed(description=f'Channel {channel.name} ({channel.mention}) was deleted', color=Color.red())
        await bot.log_channel.send(embed=embed)
    except Exception as e:
        print(f"on_guild_channel_delete Error: {e}")  

    
@bot.event
async def on_guild_role_create(role):
    try:
        # creating roles
        embed = Embed(description=f'Role {role.mention} was created', color=Color.green())
        await bot.log_channel.send(embed=embed)
    except Exception as e:
        print(f"on_guild_role_create Error: {e}")  

    
@bot.event
async def on_guild_role_delete(role):
    try:
        # deleting roles, should ping @alerts for this
        embed = Embed(description=f'Role {role.name} ({role.mention}) was deleted', color=Color.red())
        await bot.log_channel.send(embed=embed)
    except Exception as e:
        print(f"on_guild_role_delete Error: {e}")  

    
@bot.event
async def on_guild_role_update(before, after):
    try:
        # editing roles, could expand this 
        if before.name != after.name:
            embed = Embed(description=f'Role {before.mention} was renamed to {after.name}', color=Color.orange())
            await bot.log_channel.send(embed=embed)
    
        if before.permissions.administrator != after.permissions.administrator:
            # changes involving the administrator permission / sensitive permissions (can help to prevent mistakes)
            content = "<@&1108342563628404747>" # @alerts role
            embed = Embed(description=f'Role {after.mention} had its administrator permission {"enabled" if after.permissions.administrator else "disabled"}', color=Color.red())
            await bot.log_channel.send(content=content, embed=embed)  
    except Exception as e:
        print(f"on_guild_role_update Error: {e}")  

    
@bot.event
async def on_voice_state_update(member, before, after):
    try:
        if before.mute != after.mute:
            # muting members
            embed = Embed(description=f'{member} was {"muted" if after.mute else "unmuted"} in voice chat', color=Color.orange())
            await bot.log_channel.send(embed=embed)
    
        if before.deaf != after.deaf:
            # deafening members
            embed = Embed(description=f'{member} was {"deafened" if after.deaf else "undeafened"} in voice chat', color=Color.orange())
            await bot.log_channel.send(embed=embed)
    except Exception as e:
        print(f"on_voice_state_update Error: {e}")  

# github test stuff -------------------------------------------------------------------------------------------------------------------
"""
async def check_github():
    url = f'https://api.github.com/repos/{github_repo}/pulls'
    response = requests.get(url)
    pulls = response.json()

    for pull in pulls:
        # Check if the pull request was just opened
        if pull['state'] == 'open' and pull['created_at'] == pull['updated_at']:
            channel = client.get_channel(channel_id)
            if channel:
                await channel.send(f'New PR opened: {pull["title"]}')
"""
# bot stuff ---------------------------------------------------------------------------------------------------------------------------

@bot.event
async def on_ready():
    await asyncio.sleep(5)
    print('Logged on as', bot.user)
    await asyncio.sleep(5)
    bot.log_channel = bot.get_channel(1036960509586587689) # admin-logs
    await asyncio.sleep(5)
    print(bot.log_channel)

        
def run_bot():
    bot.run(DISCORD_TOKEN)

threading.Thread(target=run_bot).start()

def greet(name):
    return "Hello " + name + "!"

demo = gr.Interface(fn=greet, inputs="text", outputs="text")
demo.launch()
