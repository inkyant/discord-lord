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

async def scrape_user_messages(user_id, channel_id=None, limit=None, time_threshold_minutes=30):
    """
    Scrape messages from a specific user, combining consecutive messages and tracking preceding messages.
    Messages are grouped separately if there's a time gap greater than the threshold.
    
    Args:
        user_id: The ID of the user to scrape messages from
        channel_id: Optional ID of the channel to scrape from. If None, all channels will be searched.
        limit: Maximum number of messages to retrieve per channel (None = no limit)
        time_threshold_minutes: Time threshold in minutes to separate message groups
    
    Returns:
        A list of message data dictionaries
    """
    result_messages = []

    def save_message_group(msgs, prev_msg):
        result_messages.append({"group": [m.clean_content for m in msgs], "prev": prev_msg.clean_content if prev_msg else ""})
    
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
                    # Check if we should start a new group due to time gap
                    if current_group and (message.created_at - current_group[-1].created_at).total_seconds() > time_threshold_minutes * 60:
    
                        save_message_group(current_group, preceding_message)
                        
                        # Start a new group with the current message
                        current_group = [message]
                        # Set preceding message to the message before this one
                        if i > 0:
                            preceding_message = all_messages[i-1]
                    else:
                        # Add to current group
                        if not current_group:
                            # This is the first message in a new group
                            if i > 0:
                                preceding_message = all_messages[i-1]
                        
                        current_group.append(message)
                    
                    # If this is the last message, save the group
                    if i == len(all_messages) - 1:
                        save_message_group(current_group, preceding_message)
                    
                    # Check if next message is from a different user
                    elif i < len(all_messages) - 1 and all_messages[i+1].author.id != user_id:
                        save_message_group(current_group, preceding_message)
                        
                        # Reset for next group
                        current_group = []
                        preceding_message = None
                else:
                    # This message is from a different user
                    # If we had a group going, save it
                    if current_group:
                        save_message_group(current_group, preceding_message)
                        
                        # Reset for next group
                        current_group = []
                        preceding_message = None
            
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
    parser.add_argument('--time_gap', type=int, default=30, help='Time gap in minutes to separate message groups (default: 30)')
    
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
        time_gap_input = input("Time gap in minutes to separate message groups (default: 30): ")
        time_gap = int(time_gap_input) if time_gap_input else 30
        output = input("Output file path (default: ./data/messages.csv): ") or './data/messages.csv'
        
        class Args:
            pass
        
        args = Args()
        args.user_id = user_id
        args.channel_id = channel_id
        args.limit = limit
        args.time_gap = time_gap
        args.output = output
    
    # Scrape the messages
    messages = await scrape_user_messages(args.user_id, args.channel_id, args.limit, args.time_gap)
    
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