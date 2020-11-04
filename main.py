from config import config
import discord
import asyncio
import aiohttp
import datetime
import random
import PIL
from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw
import textwrap
import os
import uuid
from wand.image import Image as WandImage
import csv
import json
import logging
from nltk.chat.eliza import eliza_chatbot

dir_path = os.path.dirname(os.path.realpath(__file__)) # File folder path to this script

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)
logging.basicConfig(filename='staticbot.log',level=logging.INFO,format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger('StaticBot')

streaming_instance = None

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    print('Connected guilds')
    for serv in client.guilds:
        print(serv.name)
    print('------')
    
    # Cache pinned messages in #staff
    pins = await client.get_channel(config["STAFF_CHANNEL"]).pins()
    #msgs = client.connection.messages
    #for p in pins:
    #    msgs.append(p)

class CheckUser():
    def get_roles(user):
        roles = []
        guild = client.get_guild(config['GUILD_ID'])
        member = guild.get_member(user.id)
        for role in member.roles:
            roles.append(role.id)
        return roles

    async def is_admin(user): # check if user is admin
        roles = CheckUser.get_roles(user)
        if config["ADMIN_ROLE"] in roles:
            return True
        return False

    async def is_member(user):
        roles = CheckUser.get_roles(user)
        if config["MEMBER_ROLE"] in roles:
            return True
        return False

    async def is_streamer(user):
        roles = CheckUser.get_roles(user)
        if config["STREAMER_ROLE"] in roles:
            return True
        return False

class Spoiler():
    async def send_spoiler_gif(text, content, channel): # send_spoiler_gif(spoiled msg, bot msg, send to channel)
        wrapped = textwrap.wrap(text, 55)
        font = ImageFont.truetype(dir_path + "/aileron_font/Aileron-SemiBold.otf", 13)

        img_cover = Image.new("RGBA", (400, (20 * len(wrapped)) + 20), (64, 64, 64))
        draw_cover = ImageDraw.Draw(img_cover)
        draw_cover.text((10, 10), "( Hover to reveal spoiler )", (160, 160, 160), font=font)

        img_spoiler = Image.new("RGBA", (400, (20 * len(wrapped)) + 20), (64, 64, 64))
        draw_spoiler = ImageDraw.Draw(img_spoiler)
        for i, line in enumerate(wrapped):
            draw_spoiler.text((10, (20 * i) + 10), line, (160, 160, 160), font=font)

        unique = str(uuid.uuid4()) #should be unique enough...
        file_cover = "gif_tmp/img_cover_{}.png".format(unique)
        file_spoiler = "gif_tmp/img_spoiler_{}.png".format(unique)
        file_gif = "gif_tmp/{}.gif".format(unique)

        img_cover.save(file_cover)
        img_spoiler.save(file_spoiler)

        with WandImage() as wand:
            with WandImage(filename=file_cover) as cover:
                wand.sequence.append(cover)
            with WandImage(filename=file_spoiler) as spoiler:
                wand.sequence.append(spoiler)
            for cursor in range(2):
                with wand.sequence[cursor] as frame:
                    frame.delay = cursor * 9999999999999999999999999999999999999999999999999999 # setting a really long delay i guess?
            wand.type = 'optimize'
            wand.save(filename=file_gif)

        os.remove(file_cover)
        os.remove(file_spoiler)

        with open(file_gif, 'rb') as gif:
            await channel.send(content, file=discord.File(gif, "spoiler.gif"))

        os.remove(file_gif)

class Streaming():
    @classmethod
    async def create(cls):
        self = cls()
        self.activity = None
        self.streamer = None
        self.title = ""
        self.twitch_url = "https://www.twitch.tv/twitch"
        return self

    def getStreamCodes():
        streams = {}
        with open('streamcode.txt') as codefile:
            streamfile = csv.reader(codefile, delimiter=',')
            for line in streamfile:
                streams[line[0]] = line[1]
        return streams

    async def send_to_btv_site(showname, streamer):
        tumblr_url = "https://bronytv.net/api/now_streaming?api_key={}".format(config["BRONYTV_API_KEY"])
        if showname is None or streamer is None:
            payload = {'now_streaming': None}
        else:
            payload = {'now_streaming': "{} - {}".format(streamer, showname)}
        headers = {"Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(tumblr_url, data=json.dumps(payload), headers=headers):
                pass

    async def initiate(self, streamcode, streamer):
        codes = Streaming.getStreamCodes()
        if streamcode in codes:
            title = codes[streamcode]
            self.activity = discord.Streaming(name="{} - {}".format(title, streamer.name), url=self.twitch_url)
            self.streamer = streamer
            self.title = title
            await client.change_presence(activity=self.activity)
            await client.get_channel(config['MANE_CHANNEL']).send("@here\n{} is now streaming **__{}__** on http://bronytv.net/stream !".format(self.streamer.mention, self.title))
        else:
            self.activity = None
            self.streamer = None
            self.title = ""
            await client.change_presence()
            await client.get_channel(config['MANE_CHANNEL']).send("Stream is now off.")
        await Streaming.send_to_btv_site(self.title, getattr(self.streamer, 'name', None))

class Command():
    async def spoiler(message):
        content = message.content[8:]
        msg = "{} has sent a spoiler~".format(message.author.mention)
        channel = message.channel
        await message.delete()
        await Spoiler.send_spoiler_gif(content, msg, channel)

    async def markspoiler(message):
        if await CheckUser.is_admin(message.author):
            spoiled_message = await message.channel.fetch_message(message.content[12:])
            msg = "{} has marked {}'s message as a spoiler~".format(message.author.mention, spoiled_message.author.mention)
            channel = message.channel
            spoiled_content = spoiled_message.content
            await message.delete()
            await spoiled_message.delete()
            await Spoiler.send_spoiler_gif(spoiled_content, msg, channel)

    async def reversederpibooru(message):
        if "derpicdn.net/img" in message.content:
            payload = {"fizziness": 0.3, "scraper_url": message.content.split()[1]}
            async with aiohttp.ClientSession() as session:
                async with session.post("https://derpibooru.org/search/reverse.json", data=payload) as resp:
                    content = await resp.json()
                    img = content["search"][0]
                    await message.author.send("Here's your direct linked image on Derpibooru!\n{}".format("https://derpibooru.org/"+img["id"]))
        else:
            await message.channel.send("{}, I'm sorry, this is not a valid Derpibooru CDN media link.".format(message.author.mention))

    async def reqspoiler(message):
        guild = message.guild or client.get_guild(config['GUILD_ID'])
        member = message.author
        role = guild.get_role(config["SPOILER_ROLE"])
        if not isinstance(member, discord.Member):
            member = guild.get_member(member.id)
        await member.add_roles(role)
        await message.channel.send("{}, you now have access to the spoiler channel!".format(message.author.mention))

    async def reqspoilers(message):
        await Command.reqspoiler(message)

    async def reqmember(message):
        if await CheckUser.is_member(message.author):
            await message.channel.send("Hey {}! You are already a member!".format(message.author.mention))
            return
        member = message.author
        if member.avatar_url != "":
            avatar = member.avatar_url
        else:
            avatar = member.default_avatar_url

        embed = discord.Embed(title="__Member Role Request__", colour=discord.Colour(0x807bbe), description="{} has requested to obtain the Member Role!\n\n**Begin your voting!**".format(member.name))

        embed.set_author(name="{}".format(member.name), icon_url="{}".format(avatar))
        embed.set_footer(text="User ID: {}".format(member.id))

        embed.add_field(name="👍/👎", value="Agree/Disagree on {}'s member role.".format(member.name), inline=True)
        embed.add_field(name="👌/👇", value="**[Admins Only]** Instantly grant/decline member status to {}.".format(member.name), inline=True)

        guild = message.guild or client.get_guild(config['GUILD_ID'])
        staff_channel = guild.get_channel(config["STAFF_CHANNEL"])
        msg = await staff_channel.send(embed=embed)
        await message.channel.send("{}, your request has been sent! Please wait for the staff's decision on your member request!".format(message.author.mention))

        await msg.add_reaction("👍")
        await msg.add_reaction("👎")
        await msg.add_reaction("👌")
        await msg.add_reaction("👇")

        await msg.pin()

    async def sponsormember(message):
        if not await CheckUser.is_member(message.author):
            await message.channel.send("Hey {}, you are not a member yet! You cannot sponsor a member without having the member role. Why don't you request a membership status with `!reqmember`?".format(message.author.mention))
            return
        if len(message.mentions) == 0:
            await message.channel.send("{} - Please mention a user to sponsor membership.".format(message.author.mention))
            return
        sponsormember = message.author
        member = message.mentions[0]
        if member.avatar_url != "":
            avatar = member.avatar_url
        else:
            avatar = member.default_avatar_url

        embed = discord.Embed(title="__Member Role Sponsorship Request__", colour=discord.Colour(0x807bbe), description="{} has requested to sponsor **{}** for the the Member Role!\n\n**Begin your voting!**".format(sponsormember.name, member.name))

        embed.set_author(name="{}".format(member.name), icon_url="{}".format(avatar))
        embed.set_footer(text="User ID: {}".format(member.id))

        embed.add_field(name="👍/👎", value="Agree/Disagree on {}'s member role.".format(member.name), inline=True)
        embed.add_field(name="👌/👇", value="**[Admins Only]** Instantly grant/decline member status to {}.".format(member.name), inline=True)

        guild = message.guild or client.get_guild(config['GUILD_ID'])
        staff_channel = guild.get_channel(config["STAFF_CHANNEL"])
        msg = await staff_channel.send(embed=embed)
        await message.channel.send("Your request has been sent! Please wait for the staff's decision on your member sponsorship request!")

        await msg.add_reaction("👍")
        await msg.add_reaction("👎")
        await msg.add_reaction("👌")
        await msg.add_reaction("👇")

        await msg.pin()

    async def stream(message):
        msg = message.content
        if await CheckUser.is_streamer(message.author):
            game = ""
            streamer = message.author
            if len(msg.split()) > 1:
                game = msg.split()[1]
                if len(message.mentions) > 0:
                    streamer = message.mentions[0]
            global streaming_instance
            await streaming_instance.initiate(game, streamer)
        else:
            await message.channel.send("Sorry {}, you do not have the streamer role.".format(message.author.mention))

    async def stlist(message):
        if await CheckUser.is_streamer(message.author):
            global streaming_instance
            codes = Streaming.getStreamCodes()
            embed = discord.Embed(title="Stream Code List", colour=discord.Colour(0x807bbe), description="List of stream codes. Type `!stream <code>` to start streaming!")
            for code, showname in codes.items():
                embed.add_field(name=code, value=showname)
            await message.channel.send(message.author.mention, embed=embed)
        else:
            await message.channel.send("Sorry {}, you do not have the streamer role.".format(message.author.mention))

    async def news(message):
        if await CheckUser.is_streamer(message.author) or await CheckUser.is_admin(message.author):
            url = "https://bronytv.net/api/raribox?api_key={}".format(config["BRONYTV_API_KEY"])
            if len(message.content.split()) < 2:
                await message.channel.send("Hey {}, Please change the rariboard using the following command format:\n`!news <image-url> <message>` (At least one parameter is required); Message parameter of `none` to clear rariboard.".format(message.author.mention))
                return
            content = message.content.split(None, 1)[1] # truncate the command
            payload = {}
            embed = discord.Embed(title="Rariboard", colour=discord.Colour(0x252af), url="http://bronytv.net/stream")
            possible_url = content.split()[0]
            if possible_url[:8].lower() == "https://" or possible_url[:7].lower() == "http://": #assume url exists
                payload["image_url"] = possible_url
                embed.set_thumbnail(url=possible_url)
                content = content.split(None, 1) # Will truncate the url
                if len(content) > 1:
                    content = content[1]
                else:
                    content = None
            if content:
                embed.description = content
                payload["text"] = content
                if content.lower() == "none":
                    payload["text"] = "" # clear out the rariboard
            headers = {'Content-Type': 'application/json'}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=json.dumps(payload), headers=headers):
                    await message.channel.send("{}, Rariboard updated with the following values changed:".format(message.author.mention), embed=embed)
        else:
            await message.channel.send("Sorry {}, you do not have the streamer or admin role.".format(message.author.mention))

    async def pick(message):
        if message.content.find(' or ') != -1:
            options=message.content[6:].split(' or ')
            choice=random.randint(0, len(options) - 1)
            await message.channel.send('{} Ummm..... I\'ll go with **'.format(message.author.mention) + options[choice] + '**.')
        else:
            await message.channel.send("or...?")

    async def pony(message):
        await message.channel.send("Pony!")

    async def changeling(message):
        ama = client.get_user(81238021453647872)
        await message.channel.send("{} is best admin =P".format(ama.mention))

    async def tech(message):
        mirality = client.get_user(87002219613810688)
        await message.channel.send("{} is your tech god. FEAR HIM.".format(mirality.mention))

    async def bumble(message):
        await message.channel.send("Current Time is Pants-O-Clock")

    async def colgate(message):
        await message.channel.send("{} is a little dirty. Brushie Brushie Brushie! (with Colgate brand toothpaste)".format(message.author.mention))

    async def fluttershy(message):
        await message.channel.send("Bouncing baby bunnies burning brightly")

    async def rainbowdash(message):
        await message.channel.send("No! Don\'t panic! There\'s cookies and punch by the door!")

    async def brushie(message):
        await message.channel.send("{} is a little dirty. Brushie Brushie Brushie!".format(message.author.mention))

    async def roulette(message):
        await message.author.send("Looks like someone tried playing Russian Roulette with a shotgun...")
        await message.channel.send("{} is playing Russian Roulette with a shotgun...".format(message.author.mention))
        await message.author.kick()

    async def konami(message):
        await message.channel.send("Up Up Down Down Left Right Left Right B A")

    async def burn(message):
        await message.channel.send("Here, you might need this. http://www.magidglove.com/Water-Jel-Burn-Jel-Burn-Treatment-Gel-049050pp.aspx")

    async def violate(message):
        target = message.author
        if await CheckUser.is_admin(target) and len(message.mentions) > 0:
            target = message.mentions[0]

        violations = [
            'Your mane looks like a mess. Want me to brushie you all night long?',
            'Hey cutie, can I mark you all night?',
            'Oh, I\'m sorry. I thought that was a braille Cutie Mark.',
            'My name\'th Twi\'tht. Do you want to th\'ee th\'omething th\'well?']
        vmsg = random.choice(violations)
        await message.channel.send("*slides up beside {} and says **{}***".format(target.mention, vmsg))

    async def ping(message):
        await message.channel.send("{} Pong! :D".format(message.author.mention))

class Tumblr(object):
    @classmethod
    async def create(cls):
        self = cls()
        self.post_id = 0
        self.title = ""
        self.content = ""
        self.author = ""
        self.author_img_url = ""
        self.post_url = ""
        self.timestamp = 0

        self.has_new_post = False
        self.ignore_initial = True # we dont want to post on bot initialization
        await self.new_post_task()
        return self

    async def update_latest_post(self):
        tumblr_url = "https://api.tumblr.com/v2/blog/btv-news.tumblr.com/posts?api_key={}&limit=2&filter=text&tag=news".format(config["TUMBLR_API_KEY"])
        async with aiohttp.ClientSession() as session:
            async with session.get(tumblr_url) as resp:
                content = await resp.json()
                if content['meta']['status'] == 200 and content['response']['posts'][0]['id'] != self.post_id:
                    post = content['response']['posts'][0]
                    self.post_id = post['id']
                    if 'post_author' in post:
                        self.author = post['post_author']
                    else:
                        self.author = post['blog_name']
                    self.author_img_url = "http://api.tumblr.com/v2/blog/{}.tumblr.com/avatar/32".format(self.author)
                    self.post_url = post['post_url']
                    self.timestamp = post['timestamp']
                    self.content = self.get_content(post)
                    self.title = self.get_title(post)
                    self.has_new_post = True

    async def new_post_task(self): # runs the check for new post, if exist, post the post
        await self.update_latest_post()
        if self.has_new_post:
            self.has_new_post = False

            if self.ignore_initial:
                self.ignore_initial = False
                return

            tumblr_channel = client.get_channel(config["TUMBLR_CHANNEL"])

            embed = discord.Embed(title=self.title, colour=discord.Colour(0x9412b5), url=self.post_url, description=self.content, timestamp=datetime.datetime.utcfromtimestamp(self.timestamp))

            embed.set_author(name=self.author, url="http://{}.tumblr.com/".format(self.author), icon_url=self.author_img_url)
            #embed.set_footer(text="GMT")

            headlines = [
                "News flash!",
                "Ring ring ring!",
                "Hey you, check this out!",
                "New Tumblr news!",
                "Lets get right into the news!",
                "Oh goodie, what's shaken?!",
                "Today, I bring you this..."
            ]
            await tumblr_channel.send(random.choice(headlines), embed=embed)

    def get_content(self, post):
        if post['type'] == "text":
            return post['body']
        elif post['type'] == "photo":
            if len(post['caption']) >= 50:
                return post['caption'] + "\n" + post['photos']['alt_sizes'][0]['url']
            else:
                return post['photos']['alt_sizes'][0]['url']
        elif post['type'] == "quote":
            return post['text']
        elif post['type'] == "link":
            return post['description'] + "\n" + post['url']
        elif post['type'] == "chat":
            return post['body']
        elif post['type'] == "audio":
            return post['caption']
        elif post['type'] == "video":
            return post['caption']
        elif post['type'] == "answer":
            return "Answer:\n" + post['answer']
        else:
            return "Error content... This should not have happened!"

    def get_title(self, post):
        if post['type'] == "text":
            return post['title']
        elif post['type'] == "photo":
            if len(post['caption']) < 50:
                return post['caption']
            else:
                return "Photo Post"
        elif post['type'] == "quote":
            return post['quote']
        elif post['type'] == "link":
            return post['title']
        elif post['type'] == "chat":
            return post['title']
        elif post['type'] == "audio":
            return post['track_name'] + " - " + post['artist']
        elif post['type'] == "video":
            return "Video Post"
        elif post['type'] == "answer":
            return post['asking_name'] + " asks, " + post['question']
        else:
            return "Error title... This should not have happened!"

class MemberPromotion():
    async def is_valid_message(message): # check if the message is a promotion request posted by the bot
        if message.author.id == client.user.id:
            for embed in message.embeds:
                if embed.type == "rich" and (embed.title == "__Member Role Request__" or embed.title == "__Member Role Sponsorship Request__"):
                    return True
        return False

    async def run_admin_promotion(reaction, user): # promote user depending on the reaction of admin
        if reaction.emoji == "👌" or reaction.emoji == "👇":
            member_id = int(reaction.message.embeds[0].footer.text[9:])
            member = reaction.message.guild.get_member(member_id)
            role = reaction.message.guild.get_role(config["MEMBER_ROLE"])

            if reaction.emoji == "👌":
                #promote to member
                await member.add_roles(role)
                await reaction.message.channel.send("Member role has been approved for {}#{} by {}.".format(member.name, member.discriminator, user.name))
                await member.send("*Pssst* I've heard from the staff over at BronyTV that you've been given the member role!")

            if reaction.emoji == "👇":
                #demote member
                await member.remove_roles(role)
                await reaction.message.channel.send("Member role has been declined for {}#{} by {}".format(member.name, member.discriminator, user.name))
            await reaction.message.unpin()

    async def run_threshold_promotion(reaction): # promotes user if message meets criterias
        reactions = reaction.message.reactions
        reactions_parsed = {"👍": 0, "👎": 0, "👌": 0, "👇": 0}
        for react in reactions:
            if react.emoji in reactions_parsed:
                reactions_parsed[react.emoji] = react.count - 1
        if (reactions_parsed["👌"] == 0 and reactions_parsed["👇"] == 0 and reactions_parsed["👎"] == 0 and reactions_parsed["👍"] >= 4): # if only yes (4) and nothin else
            member_id = int(reaction.message.embeds[0].footer.text[9:])
            member = reaction.message.guild.get_member(member_id)
            role = reaction.message.guild.get_role(config["MEMBER_ROLE"])
            if not await CheckUser.is_member(member):
                #promote to member
                await member.add_roles(role)
                await reaction.message.channel.send("Member role has been approved for {}#{} automatically from a unison vote of 4 or more 👍s.".format(member.name, member.discriminator))
                await member.send("*Pssst* I've heard from the staff over at BronyTV that you've been given the member role!")
                await reaction.message.unpin()

@client.event
async def on_message(message):
    # Command Handler - tm of endendragon
    try:
        if len(message.content.split()) > 0: #making sure there is actually stuff in the message
            msg_cmd = message.content.split()[0].lower() # get first word im message
            if msg_cmd[0] in config["COMMAND_PREFIX"]: # test for cmd prefix
                msg_cmd = msg_cmd[1:] # remove the command prefix
                cmd = getattr(Command, msg_cmd, None) #check if cmd exist, if not its none
                if cmd: # if cmd is not none...
                    async with message.channel.typing(): #this looks nice
                        await getattr(Command, msg_cmd)(message) #actually run cmd, passing in msg obj
            elif (msg_cmd == "<@{}>".format(client.user.id) or
                  msg_cmd == "<@!{}>".format(client.user.id)): #make sure it is a mention (eliza handler)
                async with message.channel.typing():
                    user_query = message.content.split(" ", 1)[1]
                    response = eliza_chatbot.respond(user_query)
                    await message.channel.send("{}, {}".format(message.author.mention, response))
    except Exception as e:
        logger.error("Error during command %s", message.content, exc_info=e)

@client.event
async def on_reaction_add(reaction, user):
    if await MemberPromotion.is_valid_message(reaction.message):
        if await CheckUser.is_admin(user):
            await MemberPromotion.run_admin_promotion(reaction, user)
        await MemberPromotion.run_threshold_promotion(reaction)

async def tumblr_background_loop():
    await client.wait_until_ready()
    tumblr = await Tumblr.create()
    while not client.is_closed():
        await tumblr.new_post_task()
        await asyncio.sleep(120)

async def init_streaming():
    await client.wait_until_ready()
    global streaming_instance
    streaming_instance = await Streaming().create()

client.loop.create_task(tumblr_background_loop())
client.loop.create_task(init_streaming())

if __name__ == "__main__":
    client.run(config['DISCORD_BOT_TOKEN'])
