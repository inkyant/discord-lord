import discord
import csv
import os
import datetime
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up intents to access message content
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

async def scrape_user_messages(user_id, channel_id=None, limit=None):
    """
    Scrape messages from a specific user, combining consecutive messages and tracking preceding messages.
    
    Args:
        user_id: The ID of the user to scrape messages from
        channel_id: Optional ID of the channel to scrape from. If None, all channels will be searched.
        limit: Maximum number of messages to retrieve per channel (None = no limit)
    
    Returns:
        A list of message data dictionaries
    """
    result_messages = []
    
    # If specific channel provided
    if channel_id:
        channel = client.get_channel(channel_id)
        if not channel:
            print(f"Channel with ID {channel_id} not found.")
            return result_messages
        
        channels = [channel]
    else:
        # Get all text channels the bot has access to
        channels = [channel for guild in client.guilds for channel in guild.text_channels]
    
    # Iterate through all channels
    for channel in channels:
        try:
            print(f"Scraping messages from {channel.name}...")
            
            # Get all messages in the channel
            all_messages = []
            async for message in channel.history(limit=limit):
                all_messages.append(message)
            
            # Reverse to process in chronological order
            all_messages.reverse()
            
            # Variables for tracking message grouping
            current_group = []
            preceding_message = None
            
            # Process messages
            for i, message in enumerate(all_messages):
                if message.author.id == user_id and message.clean_content != "":
                    # Add to current group if this is a target user message
                    current_group.append(message)
                    
                    # If this is the first message in a potential group, set the preceding message
                    if len(current_group) == 1 and i > 0:
                        preceding_message = all_messages[i-1]
                    
                    # If this is the last message or next message is from different user, save the group
                    if i == len(all_messages) - 1 or all_messages[i+1].author.id != user_id:
                        # Combine messages in group
                        combined_content = "\n".join([msg.clean_content for msg in current_group])
                        first_msg = current_group[0]

                        if first_msg.type == discord.MessageType.reply and type(first_msg.reference.resolved) != discord.DeletedReferencedMessage:
                            preceding_message = first_msg.reference.resolved
                        
                        # Create record
                        message_data = {
                            'combined_content': combined_content,
                            'message_count': len(current_group),
                            'preceding_content': preceding_message.clean_content if preceding_message else ""
                        }
                        
                        result_messages.append(message_data)
                        
                        # Reset for next group
                        current_group = []
                        preceding_message = None
                else:
                    # Reset current group if this isn't a target user message
                    current_group = []
            
        except discord.errors.Forbidden:
            print(f"Cannot access channel {channel.name} due to permissions.")
        except Exception as e:
            print(f"Error in channel {channel.name}: {e}")
    
    return result_messages

def save_to_csv(messages, filename):
    """Save the scraped messages to a CSV file"""
    if not messages:
        print("No messages to save.")
        return
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = messages[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for message in messages:
            writer.writerow(message)
    
    print(f"Saved {len(messages)} message groups to {filename}")

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Discord Message Scraper')
    parser.add_argument('--user_id', type=int, required=True, help='User ID to scrape messages from')
    parser.add_argument('--channel_id', type=int, help='Channel ID to scrape from (optional)')
    parser.add_argument('--limit', type=int, help='Maximum number of messages to retrieve per channel')
    parser.add_argument('--output', type=str, default='./data/messages.csv', help='Output CSV file path')
    
    # Get command-line arguments
    try:
        args = parser.parse_args()
    except SystemExit:
        # If arguments are not provided, prompt for them
        import sys
        print("\nPlease provide the required parameters:")
        user_id = int(input("User ID to scrape: "))
        channel_id_input = input("Channel ID to scrape (leave blank for all channels): ")
        channel_id = int(channel_id_input) if channel_id_input else None
        limit_input = input("Message limit per channel (leave blank for no limit): ")
        limit = int(limit_input) if limit_input else None
        output = input("Output file path (default: ./data/messages.csv): ") or './data/messages.csv'
        
        class Args:
            pass
        
        args = Args()
        args.user_id = user_id
        args.channel_id = channel_id
        args.limit = limit
        args.output = output
    
    # Scrape the messages
    messages = await scrape_user_messages(args.user_id, args.channel_id, args.limit)
    
    # Add timestamp to filename if it doesn't have one
    if '.csv' in args.output:
        filename = args.output.replace('.csv', f'_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    else:
        filename = f"{args.output}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Save to CSV
    save_to_csv(messages, filename)
    
    # Exit the bot
    await client.close()

# Run the bot
def main():
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        token = input("Please enter your Discord bot token: ")
    
    try:
        client.run(token)
    except discord.errors.LoginFailure:
        print("Invalid token. Please check your DISCORD_TOKEN environment variable.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()