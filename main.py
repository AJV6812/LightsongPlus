"""Lightsong plus main file"""

import os
import base64
from dotenv import load_dotenv
import disnake
from disnake.ext import commands
import openai

load_dotenv()

chatClient = openai.OpenAI()

intents = disnake.Intents().all()
client = commands.InteractionBot(intents=intents)


# @client.slash_command(name="help", description="How to use this bot")
# async def help_command(ctx: disnake.ApplicationCommandInteraction):
#     """General Help Command"""

#     embed = disnake.Embed(
#         title="Help",
#         description="This bot tells you if you've read the book for today's Cosmeredle.\nTo use this bot, you must be on the mm",
#         colour=disnake.Colour.blue(),
#     )
#     embed.add_field(
#         name="/solveable",
#         value="This command goes to the Reading Tracker and uses that to determine if you've read the book for today's Cosmeredle. Note that IP and DNF do not count as read.",
#         inline=False,
#     )
#     embed.add_field(
#         name="/update",
#         value="If you make changes to the spreadsheet, this command will update the spreadsheet and today's character.",
#         inline=False,
#     )
#     embed.add_field(
#         name="/setname",
#         value="Records your name so you don't have to type it into /solveable each time.",
#         inline=False,
#     )
#     embed.add_field(
#         name="/pingme",
#         value="Sends you a ping when the cosmeredle updates.",
#         inline=False,
#     )
#     embed.add_field(name="/unpingme", value="Undoes /pingme.", inline=False)

#     await ctx.response.send_message("", embed=embed)


@client.event
async def on_ready():
    """Called when bot is operational"""
    await (await (await client.fetch_user(560022746973601792)).create_dm()).send(
        "Hello. I'd appreciate if you stopped pointing that thing at me."
    )


@client.listen()
async def on_button_click(interaction: disnake.MessageInteraction):
    """Called when any button is pressed"""

    print(interaction.component.custom_id)
    if (
        not interaction.component.custom_id
        or not interaction.component.custom_id.isnumeric()
    ):
        await interaction.response.send_message("Something went wrong. Please supply your own ID.")
        return

    original_message = await interaction.channel.fetch_message(
        int(interaction.component.custom_id)
    )

    if original_message.author != interaction.author:
        await interaction.response.send_message("You are not the original sender!")
        return

    await interaction.response.send_message("Waiting for GPT...", ephemeral=True)

    await interaction.message.delete()

    # Ping GPT, create modal

    base64_images = []

    for attachment in original_message.attachments:
        content_type = attachment.content_type

        if (
            isinstance(content_type, str)
            and content_type.startswith("image")
            and not content_type.startswith("image/gif")
        ):
            if not (attachment.description or "id" in original_message.content.lower()):
                base64_images.append(
                    base64.b64encode(await attachment.read()).decode("utf-8")
                )

    response = chatClient.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "Describe this image or images for someone who is visually impaired. The response should start with 'ID:'",
                    },
                ]
                + [
                    (
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{x}",
                            "detail": "low",
                        }
                    )
                    for x in base64_images
                ],
            }
        ],
    )

    await interaction.edit_original_response("Please read, edit and COPY the ID generated below into the channel. Otherwise, nobody can see it.")

    await interaction.followup.send(response.output_text, ephemeral=True, delete_after=300)


@client.event
async def on_message(message: disnake.Message):
    """Called when any message is sent"""
    id_missing = 0
    total_images = 0

    for attachment in message.attachments:
        content_type = attachment.content_type

        if (
            isinstance(content_type, str)
            and content_type.startswith("image")
            and not content_type.startswith("image/gif")
        ):
            total_images += 1
            if not (attachment.description or "id" in message.content.lower()):
                id_missing += 1

    if id_missing > 0:
        ai_gen_button = disnake.ui.Button(
            label="Generate AI Description",
            style=disnake.ButtonStyle.primary,
            custom_id=str(message.id),
        )

        if total_images == 1:
            reply = "You haven't added an image description for this image!"
        elif id_missing == total_images:
            reply = "You haven't added an image description for any of these images!"
        else:
            reply = f"You haven't added an image description to {id_missing} of these images!"

        await message.reply(reply, components=ai_gen_button)


client.run(os.environ["TOKEN"])
