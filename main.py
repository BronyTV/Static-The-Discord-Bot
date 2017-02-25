from config import config
import discord
import asyncio

client = discord.Client()

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

class Command():
    async def reqmember(message):
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
        await client.send_message(message.channel, "Your request has been sent! Please wait for the staff's decision on your member request!")

        await client.add_reaction(msg, "👍")
        await client.add_reaction(msg, "👎")
        await client.add_reaction(msg, "👌")
        await client.add_reaction(msg, "👇")
        
        await client.pin_message(msg)
    
    async def sponsormember(message):
        if not await MemberPromotion.is_member(message.author):
            await client.send_message(message.channel, "You are not a member yet! You cannot sponsor a member without having the member role. Why don't you request a membership status with `!reqmember`?")
            return
        if len(message.mentions) == 0:
            await client.send_message(message.channel, "Please mention a user to sponsor membership.")
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

class MemberPromotion():
    async def is_valid_message(message): # check if the message is a promotion request posted by the bot
        if message.author.id == client.user.id:
            for embed in message.embeds:
                if embed['type'] == "rich" and (embed['title'] == "__Member Role Request__" or embed['title'] == "__Member Role Sponsorship Request__"):
                    return True
        return False
    
    async def valid_admin(user): # check if user is admin
        roles = []
        for role in user.roles:
            roles.append(role.id)
        if config["ADMIN_ROLE"] in roles:
            return True
        return False
    
    async def is_member(user):
        roles = []
        for role in user.roles:
            roles.append(role.id)
        if config["MEMBER_ROLE"] in roles:
            return True
        return False
    
    async def run_promotion(reaction, user): # promote user depending on the reaction of admin
        if reaction.emoji == "👌" or reaction.emoji == "👇":
            member_id = reaction.message.embeds[0]["footer"]["text"][9:]
            member = discord.utils.get(reaction.message.server.members, id=member_id)
            role = discord.utils.get(reaction.message.server.roles, id=config["MEMBER_ROLE"])
            
            if reaction.emoji == "👌":
                #promote to member
                await client.add_roles(member, role)
                await client.send_message(reaction.message.channel, "Member role has been approved for {}#{} by {}.".format(member.name, member.discriminator, user.name))
            
            if reaction.emoji == "👇":
                #demote member
                await client.remove_roles(member, role)
                await client.send_message(reaction.message.channel, "Member role has been declined for {}#{} by {}".format(member.name, member.discriminator, user.name))
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

@client.event
async def on_reaction_add(reaction, user):
    if await MemberPromotion.is_valid_message(reaction.message) and await MemberPromotion.valid_admin(user):
        await MemberPromotion.run_promotion(reaction, user)

client.run(config['DISCORD_BOT_TOKEN'])
