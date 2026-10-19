import time
import logging
from telebot import TeleBot, types

import config
import monitor
import docker_monitor
import notifier

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if not config.BOT_TOKEN:
    logger.error("BOT_TOKEN is not set in .env! Please set your Telegram bot token.")

bot = TeleBot(config.BOT_TOKEN, parse_mode="HTML")


def require_admin(func):
    """Decorator to ensure only authorized admin IDs can execute bot commands."""
    def wrapper(message_or_call, *args, **kwargs):
        user_id = message_or_call.from_user.id
        if not config.is_admin(user_id):
            warning_text = (
                "⛔ <b>Access Denied</b>\n\n"
                f"Your Telegram User ID is: <code>{user_id}</code>\n"
                "You are not in the authorized admin list.\n\n"
                "<i>To enable access, add this ID to <code>ADMIN_CHAT_IDS</code> in your <code>.env</code> file.</i>"
            )
            if isinstance(message_or_call, types.CallbackQuery):
                bot.answer_callback_query(message_or_call.id, "Access Denied!", show_alert=True)
                bot.send_message(message_or_call.message.chat.id, warning_text)
            else:
                bot.reply_to(message_or_call, warning_text)
            return
        return func(message_or_call, *args, **kwargs)
    return wrapper


def get_main_keyboard() -> types.InlineKeyboardMarkup:
    """Build the interactive inline keyboard."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    b_status = types.InlineKeyboardButton("📊 Quick Status", callback_data="view_status")
    b_cpu = types.InlineKeyboardButton("⚡ CPU Details", callback_data="view_cpu")
    b_ram = types.InlineKeyboardButton("🧠 RAM / Swap", callback_data="view_ram")
    b_disk = types.InlineKeyboardButton("💾 Disk Storage", callback_data="view_disk")
    b_docker = types.InlineKeyboardButton("🐳 Docker Containers", callback_data="view_docker")
    b_top = types.InlineKeyboardButton("🔥 Top Processes", callback_data="view_top")
    b_net = types.InlineKeyboardButton("🌐 Network & IP", callback_data="view_net")
    b_refresh = types.InlineKeyboardButton("🔄 Refresh Dashboard", callback_data="view_status")

    markup.add(b_status)
    markup.add(b_cpu, b_ram)
    markup.add(b_disk, b_docker)
    markup.add(b_top, b_net)
    markup.add(b_refresh)
    return markup


def build_status_message() -> str:
    """Construct a clean, rich system status dashboard card."""
    overview = monitor.get_system_overview()
    cpu = monitor.get_cpu_stats()
    ram = monitor.get_ram_stats()
    disks = monitor.get_disk_stats()
    root_disk = disks[0] if disks else None

    load_str = ", ".join(overview["load_avg"]) if overview["load_avg"] else "N/A"
    root_disk_info = f"{root_disk['bar']} ({root_disk['used']}/{root_disk['total']})" if root_disk else "N/A"

    docker_info = "Disabled"
    if config.ENABLE_DOCKER:
        d_status = docker_monitor.get_docker_status()
        if d_status["available"]:
            docker_info = f"<b>{d_status['running']}</b> running, <b>{d_status['stopped']}</b> stopped"
        else:
            docker_info = "Docker unavailable"

    text = (
        f"🖥️ <b>Server Health: {config.SERVER_NAME}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 <b>Host:</b> <code>{overview['hostname']}</code>\n"
        f"📍 <b>Public IP:</b> <code>{overview['public_ip']}</code>\n"
        f"🐧 <b>OS:</b> {overview['os']} ({overview['arch']})\n"
        f"⏱️ <b>Uptime:</b> {overview['uptime']} | <b>Load:</b> {load_str}\n\n"
        f"⚡ <b>CPU:</b> {cpu['bar']}\n"
        f"🧠 <b>RAM:</b> {ram['bar']} ({ram['used']}/{ram['total']})\n"
        f"💾 <b>Disk:</b> {root_disk_info}\n"
        f"🐳 <b>Docker:</b> {docker_info}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ <i>Updated: {time.strftime('%H:%M:%S')}</i>"
    )
    return text


@bot.message_handler(commands=["start", "help"])
@require_admin
def handle_start(message):
    text = (
        f"👋 Welcome to <b>{config.SERVER_NAME} Health Sentinel</b>!\n\n"
        "I monitor your server's hardware performance, storage, Docker containers, and alert you on anomalies.\n\n"
        "<b>Available Commands:</b>\n"
        "• /status - General health overview\n"
        "• /cpu - Detailed CPU cores & frequency\n"
        "• /ram - Memory and Swap breakdown\n"
        "• /disk - Disk drives & partition free space\n"
        "• /docker - Container health & actions\n"
        "• /top - Top CPU and Memory processes\n"
        "• /net - Network traffic IO & IP info\n"
        "• /ping - Check latency & bot response\n\n"
        "<i>Or use the fast interactive buttons below:</i>"
    )
    bot.reply_to(message, text, reply_markup=get_main_keyboard())


@bot.message_handler(commands=["status"])
@require_admin
def handle_status(message):
    text = build_status_message()
    bot.reply_to(message, text, reply_markup=get_main_keyboard())


@bot.message_handler(commands=["cpu"])
@require_admin
def handle_cpu(message):
    cpu = monitor.get_cpu_stats()
    text = (
        f"⚡ <b>CPU Performance Details</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"• Total Usage: <b>{cpu['usage_percent']:.1f}%</b>\n"
        f"• Load Bar: {cpu['bar']}\n"
        f"• Physical Cores: <b>{cpu['physical_cores']}</b> | Logical: <b>{cpu['logical_cores']}</b>\n"
        f"• Clock Speed: <b>{cpu['frequency'] or 'N/A'}</b>\n\n"
        f"<b>Per-Core Usage:</b>\n"
    )
    for idx, usage in enumerate(cpu["per_cpu"]):
        text += f"Core {idx}: {monitor.render_progress_bar(usage, length=8)}\n"

    bot.reply_to(message, text, reply_markup=get_main_keyboard())


@bot.message_handler(commands=["ram"])
@require_admin
def handle_ram(message):
    ram = monitor.get_ram_stats()
    text = (
        f"🧠 <b>Memory & Swap Details</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>RAM (Virtual Memory):</b>\n"
        f"• Used: <code>{ram['used']}</code> / Total: <code>{ram['total']}</code>\n"
        f"• Available: <code>{ram['available']}</code>\n"
        f"• Status: {ram['bar']}\n\n"
        f"<b>Swap Memory:</b>\n"
        f"• Used: <code>{ram['swap_used']}</code> / Total: <code>{ram['swap_total']}</code>\n"
        f"• Status: {ram['swap_bar']}"
    )
    bot.reply_to(message, text, reply_markup=get_main_keyboard())


@bot.message_handler(commands=["disk"])
@require_admin
def handle_disk(message):
    disks = monitor.get_disk_stats()
    text = "💾 <b>Disk Partitions & Storage</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for d in disks:
        text += (
            f"📁 <b>{d['mount']}</b> (<code>{d['device']}</code>)\n"
            f"• Used: <code>{d['used']}</code> / Total: <code>{d['total']}</code> (Free: <code>{d['free']}</code>)\n"
            f"• Status: {d['bar']}\n\n"
        )
    bot.reply_to(message, text, reply_markup=get_main_keyboard())


@bot.message_handler(commands=["docker"])
@require_admin
def handle_docker(message):
    if not config.ENABLE_DOCKER:
        bot.reply_to(message, "🐳 Docker monitoring is disabled in config.")
        return

    d_status = docker_monitor.get_docker_status()
    if not d_status["available"]:
        bot.reply_to(message, f"🐳 {d_status['message']}")
        return

    text = (
        f"🐳 <b>Docker Containers ({d_status['running']}/{d_status['total']} Running)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    for c in d_status["containers"][:10]:
        badge = "🟢" if c["status"] == "running" else "🔴"
        text += f"{badge} <b>{c['name']}</b> ({c['status']})\n   <i>Image: {c['image']}</i>\n"
        markup.add(
            types.InlineKeyboardButton(f"🔄 Restart {c['name'][:12]}", callback_data=f"ask_restart_{c['id']}")
        )

    markup.add(types.InlineKeyboardButton("🔙 Back to Dashboard", callback_data="view_status"))
    bot.reply_to(message, text, reply_markup=markup)


@bot.message_handler(commands=["top"])
@require_admin
def handle_top(message):
    procs = monitor.get_top_processes(limit=5)
    text = "🔥 <b>Top 5 CPU Consuming Processes</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for p in procs["top_cpu"]:
        text += f"• <code>{p['pid']}</code> | <b>{p['name']}</b> ({p['user']}): <b>{p['cpu_percent']}%</b>\n"

    text += "\n🧠 <b>Top 5 RAM Consuming Processes</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for p in procs["top_mem"]:
        text += f"• <code>{p['pid']}</code> | <b>{p['name']}</b> ({p['user']}): <b>{p['mem_rss']}</b> ({p['mem_percent']:.1f}%)\n"

    bot.reply_to(message, text, reply_markup=get_main_keyboard())


@bot.message_handler(commands=["net"])
@require_admin
def handle_network(message):
    net = monitor.get_network_stats()
    ip = monitor.get_public_ip()
    text = (
        f"🌐 <b>Network Statistics</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"• Public IP: <code>{ip}</code>\n"
        f"• Data Sent: <code>{net['bytes_sent']}</code> ({net['packets_sent']:,} pkts)\n"
        f"• Data Received: <code>{net['bytes_recv']}</code> ({net['packets_recv']:,} pkts)\n"
    )
    bot.reply_to(message, text, reply_markup=get_main_keyboard())


@bot.message_handler(commands=["ping"])
@require_admin
def handle_ping(message):
    start = time.time()
    msg = bot.reply_to(message, "🏓 Pong...")
    latency = (time.time() - start) * 1000
    bot.edit_message_text(f"🏓 <b>Pong!</b> Latency: <code>{latency:.1f} ms</code>", msg.chat.id, msg.message_id)


# --- Callback Query Handlers ---

@bot.callback_query_handler(func=lambda call: True)
@require_admin
def handle_callbacks(call):
    data = call.data

    if data == "view_status":
        bot.answer_callback_query(call.id, "Refreshed!")
        try:
            bot.edit_message_text(
                build_status_message(),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_main_keyboard()
            )
        except Exception:
            pass

    elif data == "view_cpu":
        bot.answer_callback_query(call.id)
        cpu = monitor.get_cpu_stats()
        text = (
            f"⚡ <b>CPU Performance Details</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"• Total Usage: <b>{cpu['usage_percent']:.1f}%</b>\n"
            f"• Load Bar: {cpu['bar']}\n"
            f"• Physical Cores: <b>{cpu['physical_cores']}</b> | Logical: <b>{cpu['logical_cores']}</b>\n"
            f"• Clock Speed: <b>{cpu['frequency'] or 'N/A'}</b>\n\n"
            f"<b>Per-Core Usage:</b>\n"
        )
        for idx, usage in enumerate(cpu["per_cpu"]):
            text += f"Core {idx}: {monitor.render_progress_bar(usage, length=8)}\n"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back to Status", callback_data="view_status"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "view_ram":
        bot.answer_callback_query(call.id)
        ram = monitor.get_ram_stats()
        text = (
            f"🧠 <b>Memory & Swap Details</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>RAM (Virtual Memory):</b>\n"
            f"• Used: <code>{ram['used']}</code> / Total: <code>{ram['total']}</code>\n"
            f"• Available: <code>{ram['available']}</code>\n"
            f"• Status: {ram['bar']}\n\n"
            f"<b>Swap Memory:</b>\n"
            f"• Used: <code>{ram['swap_used']}</code> / Total: <code>{ram['swap_total']}</code>\n"
            f"• Status: {ram['swap_bar']}"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back to Status", callback_data="view_status"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "view_disk":
        bot.answer_callback_query(call.id)
        disks = monitor.get_disk_stats()
        text = "💾 <b>Disk Storage</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        for d in disks:
            text += (
                f"📁 <b>{d['mount']}</b> (<code>{d['device']}</code>)\n"
                f"• Used: <code>{d['used']}</code> / Total: <code>{d['total']}</code> (Free: <code>{d['free']}</code>)\n"
                f"• Status: {d['bar']}\n\n"
            )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back to Status", callback_data="view_status"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "view_docker":
        bot.answer_callback_query(call.id)
        d_status = docker_monitor.get_docker_status()
        if not d_status["available"]:
            text = f"🐳 {d_status['message']}"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back to Status", callback_data="view_status"))
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
            return

        text = (
            f"🐳 <b>Docker Containers ({d_status['running']}/{d_status['total']} Running)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
        markup = types.InlineKeyboardMarkup(row_width=2)
        for c in d_status["containers"][:10]:
            badge = "🟢" if c["status"] == "running" else "🔴"
            text += f"{badge} <b>{c['name']}</b> ({c['status']})\n"
            markup.add(
                types.InlineKeyboardButton(f"🔄 Restart {c['name'][:12]}", callback_data=f"ask_restart_{c['id']}")
            )
        markup.add(types.InlineKeyboardButton("🔙 Back to Status", callback_data="view_status"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "view_top":
        bot.answer_callback_query(call.id)
        procs = monitor.get_top_processes(limit=5)
        text = "🔥 <b>Top 5 CPU Consuming Processes</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        for p in procs["top_cpu"]:
            text += f"• <code>{p['pid']}</code> | <b>{p['name']}</b> ({p['user']}): <b>{p['cpu_percent']}%</b>\n"
        text += "\n🧠 <b>Top 5 RAM Consuming Processes</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        for p in procs["top_mem"]:
            text += f"• <code>{p['pid']}</code> | <b>{p['name']}</b> ({p['user']}): <b>{p['mem_rss']}</b> ({p['mem_percent']:.1f}%)\n"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back to Status", callback_data="view_status"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data == "view_net":
        bot.answer_callback_query(call.id)
        net = monitor.get_network_stats()
        ip = monitor.get_public_ip()
        text = (
            f"🌐 <b>Network Statistics</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"• Public IP: <code>{ip}</code>\n"
            f"• Data Sent: <code>{net['bytes_sent']}</code> ({net['packets_sent']:,} pkts)\n"
            f"• Data Received: <code>{net['bytes_recv']}</code> ({net['packets_recv']:,} pkts)\n"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back to Status", callback_data="view_status"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data.startswith("ask_restart_"):
        container_id = data.replace("ask_restart_", "")
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Confirm Restart", callback_data=f"do_restart_{container_id}"),
            types.InlineKeyboardButton("❌ Cancel", callback_data="view_docker")
        )
        bot.edit_message_text(
            f"⚠️ Are you sure you want to restart container <code>{container_id}</code>?",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

    elif data.startswith("do_restart_"):
        container_id = data.replace("do_restart_", "")
        bot.answer_callback_query(call.id, "Restarting container...")
        res = docker_monitor.restart_container(container_id)
        bot.edit_message_text(
            f"{'✅' if res['success'] else '❌'} {res['message']}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_main_keyboard()
        )


def main():
    if not config.BOT_TOKEN:
        print("\n[!] Error: BOT_TOKEN not found in .env.")
        print("[!] Please duplicate .env.example to .env and fill in your Bot Token.\n")
        return

    print("=" * 50)
    print(f"🚀 Starting {config.SERVER_NAME} Health Sentinel Bot...")
    print(f"👤 Authorized Admins: {list(config.ADMIN_CHAT_IDS) or 'None (Warning: Access Denied to all)'}")
    print(f"⏱️ Alert Interval: Every {config.CHECK_INTERVAL}s")
    print("=" * 50)

    # Launch background threshold monitoring thread
    notifier.start_monitoring_worker(bot)

    # Launch Telegram polling with automatic reconnect
    print("🤖 Bot is now online and polling for Telegram messages...")
    bot.infinity_polling(timeout=20, long_polling_timeout=20)


if __name__ == "__main__":
    main()
