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

client = discord.Client()
logging.basicConfig(filename='staticbot.log',level=logging.INFO,format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger('StaticBot')

streaming_instance = None

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    print('Connected servers')
    for serv in client.servers:
        print(serv.name)
    print('------')

class CheckUser():
    def get_roles(user):
        roles = []
        member = client.get_server(config['GUILD_ID']).get_member(user.id)
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
            await client.send_file(channel, gif, filename="spoiler.gif", content=content)

        os.remove(file_gif)

class Streaming():
    @classmethod
    async def create(cls):
        self = cls()
        self.game = None
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
            self.game = discord.Game(name="{} - {}".format(title, streamer.name), url=self.twitch_url, type=1)
            self.streamer = streamer
            self.title = title
            await client.change_presence(game=self.game)
            await client.send_message(client.get_channel(config['MANE_CHANNEL']), "@here\n{} is now streaming **__{}__** on http://bronytv.net/stream !".format(self.streamer.mention, self.title))
        else:
            self.game = None
            self.streamer = None
            self.title = ""
            await client.change_presence()
            await client.send_message(client.get_channel(config['MANE_CHANNEL']), "Stream is now off.")
        await Streaming.send_to_btv_site(self.title, getattr(self.streamer, 'name', None))

class Command():
    async def spoiler(message):
        content = message.content[8:]
        msg = "{} has sent a spoiler~".format(message.author.mention)
        channel = message.channel
        await client.delete_message(message)
        await Spoiler.send_spoiler_gif(content, msg, channel)

    async def markspoiler(message):
        if await CheckUser.is_admin(message.author):
            spoiled_message = await client.get_message(message.channel, message.content[12:])
            msg = "{} has marked {}'s message as a spoiler~".format(message.author.mention, spoiled_message.author.mention)
            channel = message.channel
            spoiled_content = spoiled_message.content
            await client.delete_message(message)
            await client.delete_message(spoiled_message)
            await Spoiler.send_spoiler_gif(spoiled_content, msg, channel)

    async def reversederpibooru(message):
        if "derpicdn.net/img" in message.content:
            payload = {"fizziness": 0.3, "scraper_url": message.content.split()[1]}
            async with aiohttp.ClientSession() as session:
                async with session.post("https://derpibooru.org/search/reverse.json", data=payload) as resp:
                    content = await resp.json()
                    img = content["search"][0]
                    await client.send_message(message.author, "Here's your direct linked image on Derpibooru!\n{}".format("https://derpibooru.org/"+img["id"]))
        else:
            await client.send_message(message.channel, "{}, I'm sorry, this is not a valid Derpibooru CDN media link.".format(message.author.mention))

    async def reqspoiler(message):
        role = discord.utils.get(message.server.roles, id=config["SPOILER_ROLE"])
        await client.add_roles(message.author, role)
        await client.send_message(message.channel, "{}, you now have access to the spoiler channel!".format(message.author.mention))

    async def reqmember(message):
        if await CheckUser.is_member(message.author):
            await client.send_message(message.channel, "Hey {}! You are already a member!".format(message.author.mention))
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

        staff_channel = discord.utils.get(message.server.channels, id=config["STAFF_CHANNEL"])
        msg = await client.send_message(staff_channel, embed=embed)
        await client.send_message(message.channel, "{}, your request has been sent! Please wait for the staff's decision on your member request!".format(message.author.mention))

        await client.add_reaction(msg, "👍")
        await client.add_reaction(msg, "👎")
        await client.add_reaction(msg, "👌")
        await client.add_reaction(msg, "👇")

        await client.pin_message(msg)

    async def sponsormember(message):
        if not await CheckUser.is_member(message.author):
            await client.send_message(message.channel, "Hey {}, you are not a member yet! You cannot sponsor a member without having the member role. Why don't you request a membership status with `!reqmember`?".format(message.author.mention))
            return
        if len(message.mentions) == 0:
            await client.send_message(message.channel, "{} - Please mention a user to sponsor membership.".format(message.author.mention))
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

        staff_channel = discord.utils.get(message.server.channels, id=config["STAFF_CHANNEL"])
        msg = await client.send_message(staff_channel, embed=embed)
        await client.send_message(message.channel, "Your request has been sent! Please wait for the staff's decision on your member sponsorship request!")

        await client.add_reaction(msg, "👍")
        await client.add_reaction(msg, "👎")
        await client.add_reaction(msg, "👌")
        await client.add_reaction(msg, "👇")

        await client.pin_message(msg)

    async def stream(message):
        msg = message.content
        if await CheckUser.is_streamer(message.author):
            game = ""
            if len(msg.split()) > 1:
                game = msg.split()[1]
            global streaming_instance
            await streaming_instance.initiate(game, message.author)
        else:
            await client.send_message(message.channel, "Sorry {}, you do not have the streamer role.".format(message.author.mention))

    async def stlist(message):
        if await CheckUser.is_streamer(message.author):
            global streaming_instance
            codes = Streaming.getStreamCodes()
            embed = discord.Embed(title="Stream Code List", colour=discord.Colour(0x807bbe), description="List of stream codes. Type `!stream <code>` to start streaming!")
            for code, showname in codes.items():
                embed.add_field(name=code, value=showname)
            await client.send_message(message.channel, message.author.mention, embed=embed)
        else:
            await client.send_message(message.channel, "Sorry {}, you do not have the streamer role.".format(message.author.mention))

    async def news(message):
        if await CheckUser.is_streamer(message.author) or await CheckUser.is_admin(message.author):
            url = "https://bronytv.net/api/raribox?api_key={}".format(config["BRONYTV_API_KEY"])
            if len(message.content.split()) < 2:
                await client.send_message(message.channel, "Hey {}, Please change the rariboard using the following command format:\n`!news <image-url> <message>` (At least one parameter is required).".format(message.author.mention))
                return
            content = message.content.split(None, 1)[1] # truncate the command
            payload = {}
            possible_url = content.split()[0].lower()
            if possible_url[:8] == "https://" or possible_url[:7] == "http://": #assume url exists
                payload["image_url"] = possible_url
                content = content.split(None, 1) # Will truncate the url
                if len(content) > 1:
                    content = content[1]
                else:
                    content = None
            if content:
                payload["text"] = content
            headers = {'Content-Type': 'application/json'}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=json.dumps(payload), headers=headers):
                    pass
        else:
            await client.send_message(message.channel, "Sorry {}, you do not have the streamer or admin role.".format(message.author.mention))
            
    async def pick(message):
        if message.content.find(' or ') != -1:
            options=message.content[6:].split(' or ')
            choice=random.randint(0, len(options) - 1)
            await client.send_message(message.channel, '{} Ummm..... I\'ll go with **'.format(message.author.mention) + options[choice] + '**.')
        else:
            await client.send_message(message.channel, "or...?")

    async def pony(message):
        await client.send_message(message.channel, "Pony!")

    async def changeling(message):
        ama = client.get_user_info("81238021453647872")
        await client.send_message(message.channel, "{} is best admin =P".format(ama.mention))

    async def tech(message):
        ama = client.get_user_info("81238021453647872")
        await client.send_message(message.channel, "{} is your tech god. FEAR HIM.".format(ama.mention))

    async def bumble(message):
        await client.send_message(message.channel, "Current Time is Pants-O-Clock")

    async def colgate(message):
        await client.send_message(message.channel, "{} is a little dirty. Brushie Brushie Brushie! (with Colgate brand toothpaste)".format(message.author.mention))

    async def fluttershy(message):
        await client.send_message(message.channel, "Bouncing baby bunies burning brightly")

    async def rainbowdash(message):
        await client.send_message(message.channel, "No! Don\'t panic! There\'s cookies and punch by the door!")

    async def brushie(message):
        await client.send_message(message.channel, "{} is a little dirty. Brushie Brushie Brushie!".format(message.author.mention))

    async def roulette(message):
        await client.send_message(message.author, "Looks like someone tried playing Russian Roulette with a shotgun...")
        await client.send_message(message.channel, "{} is playing Russian Roulette with a shotgun...".format(message.author.mention))
        await client.kick(message.author)

    async def konami(message):
        await client.send_message(message.channel, "Up Up Down Down Left Right Left Right B A")

    async def burn(message):
        await client.send_message(message.channel, "Here, you might need this. http://www.magidglove.com/Water-Jel-Burn-Jel-Burn-Treatment-Gel-049050pp.aspx")

    async def violate(message):
        if await CheckUser.is_admin(message.author):
            rndint=random.randint(1,4)
            vmsg = ""
            if rndint==1:
                vmsg='Your mane looks like a mess. Want me to brushie you all night long?'
            if rndint==2:
                vmsg='Hey cutie, can I mark you all night?'
            if rndint==3:
                vmsg='Oh, I\'m sorry. I thought that was a braille Cutie Mark.'
            if rndint==4:
                vmsg='My name\'th Twi\'tht. Do you want to th\'ee th\'omething th\'well?'
            await client.send_message(message.channel, "*slides up besides {} and says **{}***".format(message.author.mention, vmsg))

    async def ping(message):
        await client.send_message(message.channel, "{} Pong! :D".format(message.author.mention))

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

            tumblr_channel = client.get_channel(str(config["TUMBLR_CHANNEL"]))

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
            await client.send_message(tumblr_channel, random.choice(headlines), embed=embed)

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
                if embed['type'] == "rich" and (embed['title'] == "__Member Role Request__" or embed['title'] == "__Member Role Sponsorship Request__"):
                    return True
        return False

    async def run_admin_promotion(reaction, user): # promote user depending on the reaction of admin
        if reaction.emoji == "👌" or reaction.emoji == "👇":
            member_id = reaction.message.embeds[0]["footer"]["text"][9:]
            member = discord.utils.get(reaction.message.server.members, id=member_id)
            role = discord.utils.get(reaction.message.server.roles, id=config["MEMBER_ROLE"])

            if reaction.emoji == "👌":
                #promote to member
                await client.add_roles(member, role)
                await client.send_message(reaction.message.channel, "Member role has been approved for {}#{} by {}.".format(member.name, member.discriminator, user.name))
                await client.send_message(member, "*Pssst* I've heard from the staffs over at BronyTV that you've been given the member role!")

            if reaction.emoji == "👇":
                #demote member
                await client.remove_roles(member, role)
                await client.send_message(reaction.message.channel, "Member role has been declined for {}#{} by {}".format(member.name, member.discriminator, user.name))
            await client.unpin_message(reaction.message)

    async def run_threshold_promotion(reaction): # promotes user if message meets criterias
        reactions = reaction.message.reactions
        reactions_parsed = {"👍": 0, "👎": 0, "👌": 0, "👇": 0}
        for react in reactions:
            if react.emoji in reactions_parsed:
                reactions_parsed[react.emoji] = react.count - 1
        if (reactions_parsed["👌"] == 0 and reactions_parsed["👇"] == 0 and reactions_parsed["👎"] == 0 and reactions_parsed["👍"] >= 4): # if only yes (4) and nothin else
            member_id = reaction.message.embeds[0]["footer"]["text"][9:]
            member = discord.utils.get(reaction.message.server.members, id=member_id)
            role = discord.utils.get(reaction.message.server.roles, id=config["MEMBER_ROLE"])
            if not await CheckUser.is_member(member):
                #promote to member
                await client.add_roles(member, role)
                await client.send_message(reaction.message.channel, "Member role has been approved for {}#{} automatically from a unison vote of 4 or more 👍s.".format(member.name, member.discriminator))
                await client.send_message(member, "*Pssst* I've heard from the staffs over at BronyTV that you've been given the member role!")
                await client.unpin_message(reaction.message)

@client.event
async def on_message(message):
    # Command Handler - tm of endendragon
    if len(message.content.split()) > 0: #making sure there is actually stuff in the message
        msg_cmd = message.content.split()[0].lower() # get first word im message
        if msg_cmd[0] == config["COMMAND_PREFIX"]: # test for cmd prefix
            msg_cmd = msg_cmd[1:] # remove the command prefix
            cmd = getattr(Command, msg_cmd, None) #check if cmd exist, if not its none
            if cmd: # if cmd is not none...
                await client.send_typing(message.channel) #this looks nice
                await getattr(Command, msg_cmd)(message) #actually run cmd, passing in msg obj
        elif msg_cmd == "<@{}>".format(client.user.id): #make sure it is a mention (eliza handler)
            await client.send_typing(message.channel)
            user_query = message.content.split(" ", 1)[1]
            response = eliza_chatbot.respond(user_query)
            await client.send_message(message.channel, "{}, {}".format(message.author.mention, response))

@client.event
async def on_reaction_add(reaction, user):
    if await MemberPromotion.is_valid_message(reaction.message):
        if await CheckUser.is_admin(user):
            await MemberPromotion.run_admin_promotion(reaction, user)
        await MemberPromotion.run_threshold_promotion(reaction)

async def tumblr_background_loop():
    await client.wait_until_ready()
    tumblr = await Tumblr.create()
    while not client.is_closed:
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
