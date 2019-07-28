#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from discord.ext import commands
import discord
import config
import asyncio
import time
import datetime

#https://discordapp.com/oauth2/authorize?client_id=593029590205726735&scope=bot&permissions=8


class Bot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(command_prefix=commands.when_mentioned_or('.'), case_insensitive=True, **kwargs) #, formatter = CustomFormatter()
        self.remove_command('help')
        for cog in config.cogs:
            try:
                self.load_extension(cog)
                print("[*] Loaded", cog)
            except Exception as exc:
                print('Could not load extension {0} due to {1.__class__.__name__}: {1}'.format(cog, exc))

    async def on_ready(self):
        self.start_time = time.time()
        print('Logged on as {0} (ID: {0.id})'.format(self.user))


bot = Bot()


@bot.command(
    name="help",
    aliases=['?'],
    description="Returns a list of all commands and a brief description",
    usage=".help <section>",
)
async def help(ctx):
    embed = discord.Embed(colour=0x95a5a6, description="For more information, refer to [this](https://kevinissa.dev/appmonitor.html).")
    embed.set_author(name="Help")
    for command in bot.cogs["Service"].get_commands():
        embed.add_field(name=command.name, value=command.description, inline=False)
    embed.set_footer(text="Use \".more <command>\" for the syntax of a command.")
    await ctx.channel.send(embed=embed)


@bot.command(
    name="more",
    aliases=['man'],
    description="Returns information about a command",
    usage=".more <command>",
)
async def more(ctx, cmd):
    for cog in bot.cogs:
        for command in bot.cogs["Service"].get_commands():
            if cmd.lower() == command.name.lower() or cmd.lower() in command.aliases:
                embed=discord.Embed(color=0x95a5a6, description="For more information, refer to [this](https://kevinissa.dev/appmonitor.html).")
                embed.set_author(name=command.name)
                if command.aliases:
                    embed.add_field(name="Alias", value='/'.join(command.aliases), inline=True)
                embed.add_field(name="Usage", value=command.usage, inline=True)
                embed.set_footer(text=command.description)
                await ctx.channel.send(embed=embed)
                return


@bot.command(
    name="UpTime",
    aliases=['up'],
    description="How long the bot has been online for since its last reboot",
    usage=".uptime",
)
async def uptime(ctx):
    current_time = time.time()
    difference = int(round(current_time - bot.start_time))
    await ctx.channel.send(str(datetime.timedelta(seconds=difference)))


@bot.command(
    name="Invite",
    aliases=['inv'],
    description="A link for you to invite the bot to your server with!",
    usage=".invite",
)
async def invite(ctx):
    await ctx.channel.send("https://discordapp.com/oauth2/authorize?client_id=593029590205726735&scope=bot&permissions=8")

bot.run(config.token)
