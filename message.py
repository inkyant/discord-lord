import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import re

# Load environment variables from .env file
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
bot = commands.Bot(command_prefix='!', intents=intents)

# The ID of the channel to monitor
TARGET_CHANNEL_ID = 1345645691875233878  # Replace with your channel ID

from unsloth import FastLanguageModel

prompt = """Below is a snippet of an online text conversation on Discord. The text before the user's response is given. Complete the user's response to the text message.

### Previous Message:
{}

### Response:
{}"""


model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="lora_model",  # folder name with saved safetensors, etc.
    max_seq_length=2048,
    load_in_4bit=True,
)
FastLanguageModel.for_inference(model)  # Enable native 2x faster inference

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')


@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Check if the message is in the target channel
    if message.channel.id == TARGET_CHANNEL_ID:

        print("got message", message.clean_content)

        inputs = tokenizer(
            [
                prompt.format(
                    message.clean_content,  # input
                    "",  # output - leave this blank for generation!
                )
            ],
            return_tensors="pt",
        ).to("cuda")

        outputs = model.generate(**inputs, max_new_tokens=64, use_cache=True, temperature=0.99)
        generated = tokenizer.batch_decode(outputs)

        generated = str(generated[0])

        print("\n response: \n", generated)
        
        pattern = r"(?<=### Response:\n)(.*)"

        # Search for the pattern in the text
        match = re.search(pattern, str(generated), re.DOTALL)

        if match:
            generated = match.group(1) 
            generated = generated.replace(r'\\n', '\n')
            generated = generated.replace('<eos>', '')
        else:
            print("No match found")

        for line in generated.split("\n"):
            await message.channel.send(line)
    
    # Process commands
    await bot.process_commands(message)

# Run the bot
bot_token = os.getenv('DISCORD_TOKEN')
if not bot_token:
    raise ValueError("No Discord token found. Please set the DISCORD_TOKEN environment variable.")

bot.run(bot_token)