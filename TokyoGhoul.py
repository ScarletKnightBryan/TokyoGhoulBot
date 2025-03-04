import discord
from discord.ext import commands
import sqlite3
import datetime

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.messages = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Connect to SQLite database
conn = sqlite3.connect("bank.db")
c = conn.cursor()

# Create tables if not exists
c.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                AP INTEGER DEFAULT 0,
                SP INTEGER DEFAULT 0,
                yen INTEGER DEFAULT 0,
                reputation INTEGER DEFAULT 0
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount INTEGER,
                currency TEXT,
                reason TEXT,
                timestamp TEXT,
                status TEXT DEFAULT NULL
            )''')
conn.commit()

# Valid currency types
CURRENCY_TYPES = ["AP", "SP", "YEN", "REPUTATION"]



@bot.event
async def on_command_error(ctx, error):
    # Check for command errors
    if isinstance(error, commands.CommandNotFound):
        await send_embed(ctx, "Error", "❌ Unknown command. Please check your command and try again.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await send_embed(ctx, "Error", f"❌ Missing required argument. Please check the command usage.")
    elif isinstance(error, commands.BadArgument):
        await send_embed(ctx, "Error", f"❌ Invalid argument provided. Please check the command format.")
    elif isinstance(error, commands.MissingPermissions):
        await send_embed(ctx, "Error", "❌ You don't have the required permissions to use this command.")
    else:
        await send_embed(ctx, "Error", f"❌ An error occurred: {str(error)}")

    # Prevent the bot from crashing
    print(f"Error occurred: {error}")




# Check if user has administrator permission

def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

# Function to get user balance

def get_balance(user_id, currency):
    c.execute(f"SELECT {currency} FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    if result:
        return result[0]
    else:
        c.execute("INSERT INTO users (user_id, AP, SP, yen, reputation) VALUES (?, 0, 0, 0, 0)", (user_id,))
        conn.commit()
        return 0

# Function to store transaction history
def log_transaction(user_id, trans_type, amount, currency, reason=""):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO transactions (user_id, type, amount, currency, reason, timestamp) VALUES (?, ?, ?, ?, ?, ?)", 
              (user_id, trans_type, amount, currency, reason, timestamp))
    conn.commit()


# Function to embed stuff
async def send_embed(ctx, title, description):
    embed = discord.Embed(title="Tokyo Banking", color=0xce2222)
    embed.set_thumbnail(url="")
    embed.add_field(name=title, value=description, inline=False)
    await ctx.send(embed=embed)



@bot.command()
async def usercommands(ctx):
    help_text = """
    **User Commands:**

    **!deposit <currency1>,<currency2>... <amount1>,<amount2>... <reason>**  
    Deposits a specified amount into the user's account. Logs the reason for the deposit.

    **!spend <currency> <amount> <reason>**  
    Deducts a specified amount from the user's account. Logs the reason for the spending.

    **!balance [currency]**  
    Checks the balance of a specific currency or all currencies.

    **!userbalance [currency] <@user>**  
    Checks the balance of a specific currency or all currencies.

    **!history <@user> [limit]**  
    Views transaction history (default limit is 5 transactions).

    **!transfer <@user> <amount>**  
    Transfers a specified amount of Yen from the user’s account to another user. Logs the transaction details, including the sender, receiver, and amount.  
    Note: You cannot transfer Yen to yourself.

    """

    await send_embed(ctx, "Bot Commands", help_text)


@bot.command()
async def admincommands(ctx):
    help_text = """
    **Admin Commands:**

    **!give <@user> <currency> <amount>**  
    Gives the specified amount of currency to a user. Logs the transaction.

    **!giveall <currency> <amount>**  
    Distributes a specified amount of currency to all users. Logs transactions for all affected users.

    **!multi_give <currency> <amount> <@user1> <@user2> ...**  
    Gives a specified amount of currency to multiple users at once. Logs transactions for each affected user.

    **!viewallbalances**  
    Displays the balance of all users in the server.

    **!history_admin <@user> [limit]**  
    Views the transaction history of a specific user. Default limit is 5 transactions. 
    
    **!remove <currency> <amount> <member1> <member2>...**
    Allows an admin to remove a specified amount of currency from one or more users.

    **view_pending**
    Checks pending deposits.

    **approve_deposit <transaction_id1>,<transaction_id2>... <bool>**
    Allows an admin to approve multiple or one transactions.
    """
    await send_embed(ctx, "Bot Commands", help_text)



@bot.command()
async def history(ctx, limit: int = 5):
    user_id = ctx.author.id
    c.execute("SELECT type, amount, currency, reason, timestamp FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit))
    transactions = c.fetchall()

    if not transactions:
        await send_embed(ctx, "Transaction History", "📜 You have no transaction history.")
        return

    history_text = "\n".join([f"📅 {t[4]} - **{t[0].capitalize()} {t[1]} {t[2]}** | *{t[3]}*" for t in transactions])
    await send_embed(ctx, "Your Transactions", history_text)

@bot.command()
async def deposit(ctx, currencies: str, amounts: str, *, reason: str = "No reason provided"):
    # Split the input strings into lists
    currency_list = currencies.upper().split(",")
    amount_list = amounts.split(",")

    # Validate the number of currencies and amounts match
    if len(currency_list) != len(amount_list):
        await send_embed(ctx, "Error", "❌ The number of currencies and amounts don't match. Please try again.")
        return

    # Validate each currency
    for currency in currency_list:
        if currency not in CURRENCY_TYPES:
            await send_embed(ctx, "Error", f"❌ Invalid currency type! Use one of: {', '.join(CURRENCY_TYPES)}")
            return

    user_id = ctx.author.id
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # List to store formatted currency/amount pairs
    formatted_deposits = []

    # Iterate through the currencies and amounts to log the deposit
    for currency, amount_str in zip(currency_list, amount_list):
        try:
            amount = int(amount_str)  # Convert the amount to an integer
        except ValueError:
            await send_embed(ctx, "Error", f"❌ Invalid amount: {amount_str}. Please provide valid numeric values.")
            return

        # Log the deposit as pending
        c.execute("INSERT INTO transactions (user_id, type, amount, currency, reason, timestamp, status) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                  (user_id, "deposit", amount, currency, reason, timestamp, "PENDING"))
        conn.commit()

        # Format the deposit (add yen symbol and commas if it's yen)
        if currency == "YEN":
            formatted_deposit = f"YEN: ¥{amount:,}"  # Format yen with commas and prepend yen symbol
        else:
            formatted_deposit = f"{currency}: {amount:,}"  # Format other currencies with commas

        # Append formatted deposit to the list
        formatted_deposits.append(formatted_deposit)

    # Send the confirmation embed with formatted deposits
    await send_embed(ctx, "Deposit Pending", f"💰 {ctx.author.mention}, your deposits of the following currencies are pending approval:\n"
                                             + "\n".join(formatted_deposits) +
                                             f"\n**Reason:** {reason}\nPlease wait for approval from an admin.")



# Spend command
@bot.command()
async def spend(ctx, currency: str, amount: int, *, reason: str = "No reason provided"):
    currency = currency.upper()
    if currency not in CURRENCY_TYPES:
        await send_embed(ctx, "Error", f"❌ Invalid currency type! Use one of: {', '.join(CURRENCY_TYPES)}")
        return

    user_id = ctx.author.id
    balance = get_balance(user_id, currency)

    if amount > balance:
        await send_embed(ctx, "Error", f"❌ {ctx.author.mention}, you don't have enough {currency}! Current balance: {balance}")
        return

    new_balance = balance - amount
    c.execute(f"UPDATE users SET {currency}=? WHERE user_id=?", (new_balance, user_id))
    conn.commit()

    log_transaction(user_id, "spend", amount, currency, reason)
    currency_symbol = "¥" if currency == "YEN" else ""
    formatted_amount = f"{currency_symbol}{amount:,}" if currency == "YEN" else f"{amount:,} {currency}"
    formatted_balance = f"{currency_symbol}{new_balance:,}" if currency == "YEN" else f"{new_balance:,} {currency}"
    await send_embed(ctx, "Spend Successful", f"🛒 {ctx.author.mention} spent {formatted_amount} {currency}.\n**Reason:** {reason}\n**New balance:** {formatted_balance}")

#User Command: Transfer currency.
@bot.command()
async def transfer(ctx, member: discord.Member, amount: int):
    sender_id = ctx.author.id
    receiver_id = member.id

    if sender_id == receiver_id:
        await send_embed(ctx, "Transfer Failed", "❌ You cannot transfer yen to yourself.")
        return

    sender_balance = get_balance(sender_id, "yen")
    
    if amount > sender_balance:
        await send_embed(ctx, "Transfer Failed", f"❌ {ctx.author.mention}, you don't have enough yen! Current balance: ¥{sender_balance:,}")
        return

    # Update balances
    new_sender_balance = sender_balance - amount
    receiver_balance = get_balance(receiver_id, "yen") + amount


    c.execute("UPDATE users SET yen=? WHERE user_id=?", (new_sender_balance, sender_id))
    c.execute("UPDATE users SET yen=? WHERE user_id=?", (receiver_balance, receiver_id))
    conn.commit()

    # Log the transactions
    log_transaction(sender_id, "transfer_out", amount, "yen", f"Sent to {member.name}")
    log_transaction(receiver_id, "transfer_in", amount, "yen", f"Received from {ctx.author.name}")

    # Create a description for the embed
    description = (
        f"💸 {ctx.author.mention} successfully transferred ¥{amount:,} to {member.mention}.\n"
        f"**Your new balance:** ¥{new_sender_balance:,}\n"
        f"**Receiver new balance:** ¥{receiver_balance:,}"
    )

    # Send the embed message
    await send_embed(ctx, "Yen Transfer Successful", description)

@bot.command()
async def userbalance(ctx, member: discord.Member, currency: str = None):
    user_id = member.id
    if currency:
        currency = currency.upper()
        if currency not in CURRENCY_TYPES:
            await send_embed(ctx, "Error", f"❌ Invalid currency type! Use one of: {', '.join(CURRENCY_TYPES)}")
            return
        balance = get_balance(user_id, currency)
        formatted_balance = f"¥{balance:,}" if currency == "YEN" else f"{balance:,} {currency}"
        await send_embed(ctx, "Balance", f"💳 {member.name}, your {currency} balance is {formatted_balance}.")
    else:
        balance_text = "\n".join([f"**{cur}:** {'¥' + format(get_balance(user_id, cur), ',') if cur == 'YEN' else format(get_balance(user_id, cur), ',')}" for cur in CURRENCY_TYPES])
        await send_embed(ctx, "Balance", f"💳 {member.name}, your balances are:\n{balance_text}")

@bot.command()
async def balance(ctx, currency: str = None):
    user_id = ctx.author.id
    if currency:
        currency = currency.upper()
        if currency not in CURRENCY_TYPES:
            await send_embed(ctx, "Error", f"❌ Invalid currency type! Use one of: {', '.join(CURRENCY_TYPES)}")
            return
        balance = get_balance(user_id, currency)
        formatted_balance = f"¥{balance:,}" if currency == "YEN" else f"{balance:,} {currency}"
        await send_embed(ctx, "Balance", f"💳 {ctx.author.mention}, your {currency} balance is {formatted_balance}.")
    else:
        balance_text = "\n".join([f"**{cur}:** {'¥' + format(get_balance(user_id, cur), ',') if cur == 'YEN' else format(get_balance(user_id, cur), ',')}" for cur in CURRENCY_TYPES])
        await send_embed(ctx, "Balance", f"💳 {ctx.author.mention}, your balances are:\n{balance_text}")
# Admin Command: Give currency to a user
@bot.command()
@commands.has_permissions(administrator=True)
async def give(ctx, member: discord.Member, currency: str, amount: int):
    currency = currency.upper()
    if currency not in CURRENCY_TYPES:
        await send_embed(ctx, "Error", f"❌ Invalid currency type! Use one of: {', '.join(CURRENCY_TYPES)}")
        return

    user_id = member.id
    balance = get_balance(user_id, currency)
    new_balance = balance + amount

    c.execute(f"UPDATE users SET {currency}=? WHERE user_id=?", (new_balance, user_id))
    conn.commit()
    log_transaction(user_id, "admin_give", amount, currency, f"Given by {ctx.author.name}")
    currency_symbol = "¥" if currency == "YEN" else ""
    formatted_amount = f"{currency_symbol}{amount:,}" if currency == "YEN" else f"{amount:,} {currency}"
    formatted_balance = f"{currency_symbol}{new_balance:,}" if currency == "YEN" else f"{new_balance:,} {currency}"
    await send_embed(ctx, "Transaction Successful", f"✅ {ctx.author.mention} gave {formatted_amount} {currency} to {member.mention}.\n**New balance:** {formatted_balance}")


# Admin command to approve or deny deposits
@bot.command()
@commands.has_permissions(administrator=True)
async def approve_deposit(ctx, transaction_ids: str, approve: bool):
    # Split transaction IDs and convert to integers
    transaction_id_list = transaction_ids.split(",")
    
    # Track results
    approved_transactions = []
    denied_transactions = []
    errors = []

    for transaction_id in transaction_id_list:
        try:
            transaction_id = int(transaction_id.strip())  # Convert to integer
            # Fetch the transaction details
            c.execute("SELECT user_id, amount, currency FROM transactions WHERE id=? AND status='PENDING'", (transaction_id,))
            transaction = c.fetchone()

            if not transaction:
                errors.append(f"❌ No pending transaction found with ID {transaction_id}.")
                continue

            user_id, amount, currency = transaction
            status = "APPROVED" if approve else "DENIED"

            # Update transaction status
            c.execute("UPDATE transactions SET status=? WHERE id=?", (status, transaction_id))
            conn.commit()
            
            user = ctx.guild.get_member(user_id)  # Get the user object by user_id

            # Format amount correctly (add yen symbol and commas if necessary)
            if currency == "YEN":
                formatted_amount = f"¥{amount:,}"
            else:
                formatted_amount = f"{amount:,} {currency}"

            if approve:
                # If approved, update user balance
                new_balance = get_balance(user_id, currency) + amount
                c.execute(f"UPDATE users SET {currency}=? WHERE user_id=?", (new_balance, user_id))
                conn.commit()

                # Format new balance correctly
                if currency == "YEN":
                    formatted_balance = f"¥{new_balance:,}"
                else:
                    formatted_balance = f"{new_balance:,} {currency}"

                approved_transactions.append(f"✅ **{formatted_amount}** approved by {ctx.author.mention} from {user.mention}(New balance: **{formatted_balance}**)")

            else:
                denied_transactions.append(f"❌ **{formatted_amount}** denied by {ctx.author.mention} from {user.mention}")

        except ValueError:
            errors.append(f"❌ Invalid transaction ID: {transaction_id}. Please use numeric values.")

    # Build the response message
    response = []
    if approved_transactions:
        response.append("### ✅ Approved Transactions:\n" + "\n".join(approved_transactions))
    if denied_transactions:
        response.append("### ❌ Denied Transactions:\n" + "\n".join(denied_transactions))
    if errors:
        response.append("### ⚠️ Errors:\n" + "\n".join(errors))

    await send_embed(ctx, "Deposit Approval Results", "\n\n".join(response) if response else "No transactions processed.")


# Admin command to view all pending transactions
@bot.command()
@commands.has_permissions(administrator=True)
async def view_pending(ctx):
    c.execute("SELECT id, user_id, amount, currency, reason, timestamp FROM transactions WHERE status='PENDING'")
    pending_transactions = c.fetchall()

    if not pending_transactions:
        await send_embed(ctx, "No Pending Deposits", "📜 No deposits are pending approval.")
        return

    pending_text = ""
    for transaction in pending_transactions:
        user_id = transaction[1]
        user = ctx.guild.get_member(user_id)  # Get the user object by user_id

        if user:
            username = user.name  # Get the username
            mention = user.mention  # Use mention for clickable link
        else:
            username = f"Unknown user ({user_id})"
            mention = "Unknown user"

        pending_text += f"ID: {transaction[0]} | {mention} | {transaction[2]} {transaction[3]} | Reason: {transaction[4]} | Time: {transaction[5]}\n"

    await send_embed(ctx, "Pending Deposits", pending_text)



#Admin Command: Give all users. 
@bot.command()
@commands.has_permissions(administrator=True)
async def giveall(ctx, currency: str, amount: int):
    currency = currency.upper()
    if currency not in CURRENCY_TYPES:
        await send_embed(ctx, "Error", f"❌ Invalid currency type! Use one of: {', '.join(CURRENCY_TYPES)}")
        return

    c.execute("UPDATE users SET {} = {} + ?".format(currency, currency), (amount,))
    conn.commit()

    # Fetch all user IDs
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()

    for (user_id,) in users:
        log_transaction(user_id, "admin_giveall", amount, currency, f"Given to all users by {ctx.author.name}")
    currency_symbol = "¥" if currency == "YEN" else ""
    formatted_amount = f"{currency_symbol}{amount:,}" if currency == "YEN" else f"{amount:,} {currency}"
    await send_embed(ctx, "Give All", f"✅ {ctx.author.mention} gave {formatted_amount} {currency} to all users!")

#Admin Command: Give multiple users' balances.
@bot.command()
@commands.has_permissions(administrator=True)
async def multi_give(ctx, currency: str, amount: int, *members: discord.Member):
    currency = currency.upper()
    if currency not in CURRENCY_TYPES:
        await send_embed(ctx, "Error", f"❌ Invalid currency type! Use one of: {', '.join(CURRENCY_TYPES)}")
        return

    for member in members:
        user_id = member.id
        balance = get_balance(user_id, currency)
        new_balance = balance + amount

        c.execute("UPDATE users SET {}=? WHERE user_id=?".format(currency), (new_balance, user_id))
        conn.commit()
        log_transaction(user_id, "admin_multi_give", amount, currency, f"Given by {ctx.author.name}")
        currency_symbol = "¥" if currency == "YEN" else ""
        formatted_amount = f"{currency_symbol}{amount:,}" if currency == "YEN" else f"{amount:,} {currency}"
    await send_embed(ctx, "Multi Give", f"✅ {ctx.author.mention} gave {formatted_amount} {currency} to {', '.join([member.mention for member in members])}.")

# Admin Command: Check all users' balances.
@bot.command()
@commands.has_permissions(administrator=True)
async def viewallbalances(ctx):
    c.execute("SELECT user_id, AP, SP, yen, reputation FROM users")
    users = c.fetchall()

    if not users:
        await ctx.send("📊 No users found in the database.")
        return

    balance_text = "\n".join([f"<@{u[0]}> - AP: {u[1]:,}, SP: {u[2]:,}, Yen: \u00a5{u[3]:,}, Reputation: {u[4]:,}" for u in users])
    await ctx.send(f"📊 **All Users' Balances:**\n{balance_text}")



# Admin Command: View any user's transaction history.
@bot.command()
@commands.has_permissions(administrator=True)
async def history_admin(ctx, member: discord.Member, limit: int = 5):
    user_id = member.id
    c.execute("SELECT type, amount, currency, reason, timestamp FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit))
    transactions = c.fetchall()
    if not transactions:
        await send_embed(ctx, "Transaction History", f"📜 No transactions found for {member.mention}.")
        return

    history_text = "\n".join([f"📅 `{t[4]}` - **{t[0].capitalize()} {t[1]:,} {'¥' if t[2] == 'YEN' else t[2]}** | *{t[3]}*" for t in transactions])
    
    await send_embed(ctx, "Transaction History", f"📜 {ctx.author.mention}, transactions for {member.mention}:\n{history_text}")


#Admin Command: Remove any user's transaction history.
@bot.command()
@commands.has_permissions(administrator=True)
async def remove(ctx, currency: str, amount: int, *members: discord.Member):
    if not members:
        await send_embed(ctx, "Error", "You must specify at least one member.")
        return

    for member in members:
        user_id = member.id
        current_balance = get_balance(user_id, currency)

        if current_balance == 0:
            await send_embed(ctx, "Error", f"{member.mention} already has 0 {currency}. Cannot remove more.")
            continue  # Skip this user and move to the next

        new_balance = max(0, current_balance - amount)
        c.execute("UPDATE users SET {}=? WHERE user_id=?".format(currency), (new_balance, user_id))
        conn.commit()
        log_transaction(user_id, "admin_remove", -amount, currency, f"Removed by {ctx.author.name}")
        currency_symbol = "¥" if currency == "YEN" else ""
        formatted_amount = f"{currency_symbol}{amount:,}" if currency == "YEN" else f"{amount:,} {currency}"
        formatted_balance = f"{currency_symbol}{new_balance:,}" if currency == "YEN" else f"{new_balance:,} {currency}"
        await send_embed(ctx, "Admin Action", 
                         f"{formatted_amount} {currency} removed from {member.mention}.\n"
                         f"New balance: {formatted_balance}.")

@bot.command()
@commands.has_permissions(administrator=True)
async def approve(ctx, user_id: int, *, reason: str):
    c.execute("SELECT currency, amount FROM transactions WHERE user_id=? AND reason=? AND type='deposit' AND status IS NULL", (user_id, reason))
    rows = c.fetchall()
    if not rows:
        await send_embed(ctx, "Error", "❌ No matching deposit requests found.")
        return
    
    for currency, amount in rows:
        c.execute(f"UPDATE users SET {currency} = {currency} + ? WHERE user_id = ?", (amount, user_id))
    c.execute("UPDATE transactions SET status='approved' WHERE user_id=? AND reason=? AND type='deposit'", (user_id, reason))
    conn.commit()
    
    user = await bot.fetch_user(user_id)
    await send_embed(ctx, "Approval", f"✅ Approved deposits for <@{user_id}>.")
    await user.send(f"✅ Your deposits have been approved!")

@bot.command()
@commands.has_permissions(administrator=True)
async def reject(ctx, user_id: int, *, reason: str = "No reason provided"):
    c.execute("UPDATE transactions SET status='rejected' WHERE user_id=? AND reason=? AND type='deposit' AND status IS NULL", (user_id, reason))
    conn.commit()
    
    user = await bot.fetch_user(user_id)
    await send_embed(ctx, "Rejection", f"❌ Rejected deposits for <@{user_id}>.")
    await user.send(f"❌ Your deposit request was rejected. Reason: {reason}")



# Run bot
bot.run("")
