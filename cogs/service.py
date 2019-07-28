import discord
from discord.ext import commands
import asyncio
import os
import json
import aiohttp
import gspread
from oauth2client.service_account import ServiceAccountCredentials as sac

class Service(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            'https://www.googleapis.com/auth/spreadsheets',
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
            ]
        self.creds = sac.from_json_keyfile_name("creds.json", self.scope)
        self.client = gspread.authorize(self.creds)
        self.spreadsheet = self.client.open("AppMonitor") # .get_worksheet(1)

    async def error_embed(self, title=None, description=None, author=None, author_url=None, author_icon=None, footer=None):
        embed = discord.Embed(color=0xe74c3c)
        if title:
            embed.title = title
        if description:
            embed.description = description
        if author:
            if author_url and author_icon:
                embed.set_author(name=author, url=author_url, icon_url=author_icon)
            elif author_url:
                embed.set_author(name=author, url=author_url)
            elif author_icon:
                embed.set_author(name=author, icon_url=author_icon)
            else:
                embed.set_author(name=author)
        if footer:
            embed.set_footer(text=footer)
        return embed


    async def fetch_version(self, bundle_id, country):
        """ Fetch the latest version of bundle ID from appropriate store """
        info_url = "https://itunes.apple.com/" + country + "/lookup?bundleId=" + bundle_id
        async with aiohttp.ClientSession() as session:
            async with session.get(info_url) as resp:
                info = json.loads(await resp.read())
        return info['results'][0]['version']


    async def add_entry(self, ctx, id, bundle_id, country):
        """ Add an entry """
        if len(self.spreadsheet.worksheet(id).get_all_records()) > 49:
            await ctx.channel.send(embed=await self.error_embed(description="You've exceeded the maximum amount of applications!", author=ctx.message.author, author_icon=ctx.message.author.avatar_url))
            return False
        try:
            self.spreadsheet.worksheet(id).find(bundle_id)
            await ctx.channel.send(embed=await self.error_embed(description="You've already added that application!", author=ctx.message.author, author_icon=ctx.message.author.avatar_url))
            return False
        except gspread.exceptions.CellNotFound:
            pass
        info_url = "https://itunes.apple.com/" + country + "/lookup?bundleId=" + bundle_id
        async with aiohttp.ClientSession() as session:
            async with session.get(info_url) as resp:
                info = json.loads(await resp.read())
        if info['resultCount'] == 1:
            self.spreadsheet.worksheet(id).append_row([
                bundle_id,
                info['results'][0]['trackName'],
                info['results'][0]['version'],
                country,
                info['results'][0]['artworkUrl512'],
                info['results'][0]['trackViewUrl'],
                "0"
                ])
            return info


    async def add_user(self, id):
        self.spreadsheet.add_worksheet(title=id, rows="0", cols="0")
        self.spreadsheet.worksheet(id).append_row(["bundle_id", "name", "version", "country", "icon", "url", "notified"])


    async def remove_entry(self, id, bundle_id):
        """ Remove an entry """
        try:
            cell = self.spreadsheet.worksheet(id).find(bundle_id)
        except gspread.exceptions.CellNotFound:
            return
        info = self.spreadsheet.worksheet(id).row_values(cell.row)
        self.spreadsheet.worksheet(id).delete_row(cell.row)
        return info


    async def update_entry(self, id, bundle_id):
        """ Update the local version of an entry """
        try:
            cell = self.spreadsheet.worksheet(id).find(bundle_id)
        except gspread.exceptions.CellNotFound:
            return
        version = await self.fetch_version(bundle_id, self.spreadsheet.worksheet(id).cell(cell.row, 4).value)
        self.spreadsheet.worksheet(id).update_cell(cell.row, 3, "'" + version)
        self.spreadsheet.worksheet(id).update_cell(cell.row, 7, "'" + "0")
        return self.spreadsheet.worksheet(id).row_values(cell.row)


    async def notify(self):
        await asyncio.sleep(5)
        while True:
            for user in self.spreadsheet.worksheets()[1:]:
                for application in user.get_all_records():
                    if application["notified"] == 0:
                        latest_version = await self.fetch_version(application["bundle_id"], application['country'])
                        if latest_version != str(application["version"]):
                            embed = discord.Embed(title="Update Available!", color=0x1C89F5)
                            embed.set_author(name=application['name'], url=application['url'], icon_url=application['icon'])
                            embed.set_footer(text="Latest version: v" + latest_version)
                            # a = self.bot.get_user(int(user))
                            # print(a)
                            await self.bot.get_user(int(user.title)).send(embed=embed)
                            cell = user.find(application["bundle_id"])
                            user.update_cell(cell.row, 7, "'" + "1")
            await asyncio.sleep(60*3)


    async def refresh_token(self):
        while True:
            await asyncio.sleep(3800)
            self.creds = sac.from_json_keyfile_name("creds.json", self.scope)
            self.client = gspread.authorize(self.creds)
            self.client.login()
            self.spreadsheet = self.client.open("AppMonitor")


    @commands.cooldown(1, 5, type=commands.BucketType.user)
    @commands.command(
        name="Watch-List",
        description="Your personal watch-list, can be sorted by sort_keys: 'name', 'version' or 'bundle_id'. Or 'o' for only outdated applications.",
        usage=".watch *<sort_key>",
        aliases=["watchlist", "wl"],
        )
    async def watch(self, ctx, *sort):
        first = True
        back_emoji = "\U00002b05"
        forward_emoji = "\U000027a1"
        close_emoji = "\U0001f6ab"
        page = 0
        reverse = False
        outdated_count = 0
        id = str(ctx.message.author.id)
        if not id in [worksheet.title for worksheet in self.spreadsheet.worksheets()]:
            await self.add_user(id)
        if ctx.message.author.name.endswith('s'):
            suffix = "'"
        else:
            suffix = "'s"
        raw_data = self.spreadsheet.worksheet(id).get_all_records()
        if not raw_data:
            no_data_embed = await self.error_embed(description="You have not added any applications!", author=ctx.message.author.name, author_icon=ctx.message.author.avatar_url)
            await ctx.channel.send(embed=no_data_embed)
            return
        if sort:
            sortings = ["name", "version", "bundle_id", "bundle"]
            if sort[0] in sortings:
                if sort[0] == "bundle":
                    sorting = "bundle_id"
                else:
                    sorting = sort[0]
            else:
                sorting = "notified"
                reverse = True
            outdated_aliases = ["o", "out", "outdated", "old"]
            if sort[0] in outdated_aliases:
                outdated_only = True
        else:
            sorting = "notified"
            reverse = True
            outdated_only = False
        sorted_data = sorted(raw_data, key=lambda x: str(x[sorting]).lower(), reverse=reverse)
        data = [sorted_data[x:x+10] for x in range(0, len(sorted_data), 10)]
        while True:
            fetching_embed = discord.Embed(color=0xe67e22, description="Fetching data...")
            fetching_embed.set_author(name=ctx.message.author.name, icon_url=ctx.message.author.avatar_url)
            if first:
                msg = await ctx.channel.send(embed=fetching_embed)
                first = False
            else:
                await msg.edit(embed=fetching_embed)
            emoji_options = []
            if page > 0 :
                emoji_options.append(back_emoji)
            embed = discord.Embed(color=0x2ecc71)
            embed.set_author(name="{}{} Watch-List ({}/{})".format(ctx.message.author.name, suffix, page+1, len(data)), icon_url=ctx.message.author.avatar_url)
            for app in data[page]:
                latest_version = await self.fetch_version(app["bundle_id"], app["country"])
                if str(app["version"]) == latest_version:
                    if outdated_only:
                        continue
                    embed.add_field(name=app['name'], value="[{}]({})  |  v{}  |  \u2705".format(app["bundle_id"], app["url"], app['version']), inline=False)
                    # await ctx.channel.send(f"[{index}] " + app['name'] + " | " + app['version'])
                else:
                    embed.add_field(name=app['name'], value="[{}]({})  |  v{}  |  \u2B06".format(app["bundle_id"], app["url"], app['version']), inline=False)
                    embed.color=0xe67e22
                    outdated_count+=1
            if outdated_only and outdated_count == 0:
                embed = await self.error_embed(description="You have no outdated applications!", author=ctx.message.author.name, author_icon=ctx.message.author.avatar_url)
                await msg.edit(embed=embed)
                return
            await msg.edit(embed=embed)
            if 0 <= page < len(data)-1:
                emoji_options.append(forward_emoji)
            emoji_options.append(close_emoji)
            for emoji in emoji_options:
                await msg.add_reaction(emoji)
            def check(reaction, user):
                if str(reaction.emoji) not in emoji_options or user != ctx.message.author:
                    if user != ctx.bot.user:
                        self.bot.loop.create_task(msg.remove_reaction(str(reaction.emoji), user))
                return user == ctx.message.author and str(reaction.emoji) in emoji_options and reaction.message.id == msg.id
            try:
                reaction = await ctx.bot.wait_for('reaction_add', timeout=50.0, check=check)
            except asyncio.TimeoutError:
                expired_embed = await self.error_embed(description="Watch-List Session Expired", author=ctx.message.author.name, author_icon=ctx.message.author.avatar_url)
                await msg.edit(embed=expired_embed)
                await msg.clear_reactions()
                return
            await msg.clear_reactions()
            if reaction[0].emoji == forward_emoji:
                page += 1
            elif reaction[0].emoji == back_emoji:
                page -= 1
            elif reaction[0].emoji == close_emoji:
                closed_embed = await self.error_embed(description="Watch-List Closed", author=ctx.message.author.name, author_icon=ctx.message.author.avatar_url)
                await msg.edit(embed=closed_embed)
                await msg.clear_reactions()
                return


    @watch.error
    async def watch_error_handler(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("Hold on! You're on cooldown.")


    @commands.command(
        name="Add",
        description="Adds an application to your watch-list",
        usage=".add <bundle identifier> *<country>",
        aliases=["a"],
        )
    async def add(self, ctx, *bundle_ids):
        if len(bundle_ids) == 0 or len(bundle_ids) > 11:
            return
        id = str(ctx.message.author.id)
        if not id in [worksheet.title for worksheet in self.spreadsheet.worksheets()]:
            await self.add_user(id)
        if ctx.message.author.name.endswith('s'):
            suffix = "'"
        else:
            suffix = "'s"
        if len(bundle_ids) > 1:
            valid_country = False
            for country_list in self.spreadsheet.worksheet("countries").get_all_records():
                if bundle_ids[-1].lower() == country_list["country"]:
                    country = country_list["code"].lower()
                    valid_country = True
                    break
                elif bundle_ids[-1].lower() == country_list["country"]:
                    country = country_list["code"].lower()
                    valid_country = True
                    break
            if not valid_country:
                country = "us"
        else:
            country = "us"
        if len(bundle_ids) == 1:
            added = await self.add_entry(ctx, str(ctx.message.author.id), bundle_ids[0], country)
            if added != False:
                embed = discord.Embed(color=0x2ecc71)
                embed.set_author(name=added['results'][0]['trackName'], url=added['results'][0]['trackViewUrl'], icon_url=added['results'][0]['artworkUrl512'])
                embed.set_footer(text="Added to {}{} watch-list.".format(ctx.message.author.name, suffix))
            elif added == None:
                embed = await self.error_embed(description="Application not found!", author=ctx.message.author.name, author_icon=ctx.message.author.avatar_url)
            else:
                return
        else:
            added_applications = []
            if valid_country:
                for bundle_id in bundle_ids[0:-1]:
                    added = await self.add_entry(ctx, str(ctx.message.author.id), bundle_id, country)
                    if added != False:
                        added_applications.append(added['results'][0]['trackName'])
                    else:
                        return
            else:
                for bundle_id in bundle_ids:
                    added = await self.add_entry(ctx, str(ctx.message.author.id), bundle_id, country)
                    if added:
                        added_applications.append(added['results'][0]['trackName'])
                    else:
                        return
            if added_applications:
                if len(added_applications) == 1:
                    embed = discord.Embed(color=0x2ecc71)
                    embed.set_author(name=added['results'][0]['trackName'], url=added['results'][0]['trackViewUrl'], icon_url=added['results'][0]['artworkUrl512'])
                elif len(added_applications) > 1:
                    embed = discord.Embed(color=0x2ecc71, description=", ".join(added_applications))
                    embed.set_author(name="Applications Added")
                embed.set_footer(text="Added to {}{} watch-list.".format(ctx.message.author.name, suffix))
            else:
                embed = await self.error_embed(description="Application not found!", author=ctx.message.author.name, author_icon=ctx.message.author.avatar_url)
        await ctx.channel.send(embed=embed)


    @commands.command(
        name="Update",
        description="Updates an application's version in your watch-list to the latest version",
        usage=".update <bundle identifier>",
        aliases=["u"],
        )
    async def update(self, ctx, bundle_id):
        id = str(ctx.message.author.id)
        if not id in [worksheet.title for worksheet in self.spreadsheet.worksheets()]:
            await self.add_user(id)
        if ctx.message.author.name.endswith('s'):
            suffix = "'"
        else:
            suffix = "'s"
        updated = await self.update_entry(id, bundle_id)
        if updated:
            embed = discord.Embed(color=0x2ecc71)
            embed.set_author(name=updated[1], url=updated[5], icon_url=updated[4])
            embed.set_footer(text="Updated {}{} watch-list.".format(ctx.message.author.name, suffix))
        else:
            embed = await self.error_embed(description="Application not found!", author=ctx.message.author.name, author_icon=ctx.message.author.avatar_url)
        await ctx.channel.send(embed=embed)


    @commands.command(
        name="Remove",
        description="Removes an application from your watch-list",
        usage=".remove <bundle identifier>",
        aliases=["r"],
        )
    async def remove(self, ctx, bundle_id):
        id = str(ctx.message.author.id)
        if not id in [worksheet.title for worksheet in self.spreadsheet.worksheets()]:
            await self.add_user(id)
        if ctx.message.author.name.endswith('s'):
            suffix = "'"
        else:
            suffix = "'s"
        removed = await self.remove_entry(id, bundle_id)
        if removed:
            embed = await self.error_embed(author=removed[1], author_url=removed[5], author_icon=removed[4], footer="Removed from {}{} watch-list.".format(ctx.message.author.name, suffix))
        else:
            embed = await self.error_embed(description="Application not found!", author=ctx.message.author.name, author_icon=ctx.message.author.avatar_url)
        await ctx.channel.send(embed=embed)


    # @commands.command(
    #     name="countries",
    #     description="Lists the supported countries in the App Store",
    #     usage=".countries",
    #     )
    # async def countries(self, ctx):
    #     embed = discord.Embed(color=0x95a5a6, description=", ".join(country[0] for country in self.countries))
    #     embed.set_author(name="Countries")
    #     await ctx.channel.send(embed=embed)


    @commands.command(
        name="Search",
        description="Search the App Store for an application",
        usage=".search <name> *<country>",
        aliases=["s", "find"]
        )
    async def search(self, ctx, name, *country):
        emoji_options = ["\u2705"]
        if not country:
            country = "us"
        else:
            valid_country = False
            for country_list in self.spreadsheet.worksheet("countries").get_all_records():
                if country[0].lower() == country_list["country"]:
                    country = country_list["code"].lower()
                    valid_country = True
                    break
                elif country[0].lower() == country_list["country"]:
                    country = country_list["code"].lower()
                    valid_country = True
                    break
            if not valid_country:
                country = "us"
        url = "https://itunes.apple.com/search?term=" + name + "&entity=software&country=" + country
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                info = json.loads(await resp.read())
        for app in info["results"]:
            embed=discord.Embed(title=app["trackName"], url=app["trackViewUrl"], color=0x1C89F5)
            embed.set_thumbnail(url=app["artworkUrl100"])
            embed.add_field(name="Bundle ID", value=app["bundleId"], inline=True)
            try:
                embed.add_field(name="Price", value=app["formattedPrice"], inline=True)
            except:
                embed.add_field(name="Price", value="Unknown", inline=True)
            try:
                embed.add_field(name="Rating", value=f"{app['averageUserRating']}/5 of out {app['userRatingCount']} ratings", inline=True)
            except:
                embed.add_field(name="Rating", value="N/A", inline=True)
            try:
                embed.add_field(name="Update Date", value=app["currentVersionReleaseDate"], inline=True)
            except:
                embed.add_field(name="Update Date", value="N/A", inline=True)
            embed.set_footer(text=f"v{app['version']} by {app['sellerName']}")
            msg = await ctx.channel.send(embed=embed)
            def check(reaction, user):
                if str(reaction.emoji) not in emoji_options or user != ctx.message.author:
                    if user != ctx.bot.user:
                        self.bot.loop.create_task(msg.remove_reaction(str(reaction.emoji), user))
                return user == ctx.message.author and str(reaction.emoji) in emoji_options and reaction.message.id == msg.id
            await msg.add_reaction(emoji_options[0])
            try:
                reaction = await ctx.bot.wait_for('reaction_add', timeout=30.0, check=check)
            except asyncio.TimeoutError:
                await msg.remove_reaction(emoji_options[0], ctx.guild.me)
                return
            if str(reaction[0].emoji) == emoji_options[0]:
                self.bot.loop.create_task(ctx.invoke(self.bot.get_command("add"), app["bundleId"]))
            break


    @commands.command(
        name="Source",
        aliases=['src', 'donate'],
        description="Information about the bot & author",
        usage=".source",
    )
    async def source(self, ctx):
        author = ctx.bot.get_user(532986528415088660)
        embed = discord.Embed(color=0x3498db, description="This bot was coded in Python by {}.".format(author))
        embed.add_field(name="Donate", value="[You can donate to me here \u2764](https://www.paypal.me/issa741)", inline=True)
        embed.add_field(name="Twitter", value="[Follow me on Twitter! \U0001f604](https://twitter.com/KevinIssaDev)", inline=True)
        await ctx.channel.send(embed=embed)



def setup(bot):
    cog=Service(bot)
    bot.add_cog(cog)
    bot.loop.create_task(cog.refresh_token())
    bot.loop.create_task(cog.notify())
