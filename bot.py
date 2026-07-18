# -*- coding: utf-8 -*-
# Telegram Bot bán tài khoản AI (bot.py) - Phiên bản File-Based (Không cần DB & Backend)
# Quản lý kho qua file accounts.txt và lưu lịch sử bán qua sold_accounts.txt.

import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import random
import os
import datetime
import html

# ==================== CẤU HÌNH CỬA HÀNG BOT TELEGRAM ====================
# Điền Token Bot của bạn tạo từ @BotFather vào đây
BOT_TOKEN = "5552327462:AAE7gPWPzlXwn4zUQRGIp5ezoprmu9ADjkQ"

# Cấu hình thanh toán VietQR ngân hàng của bạn
BANK_ID = "MBBank"
BANK_ACCOUNT_NO = "123456789"
BANK_ACCOUNT_NAME = "NGUYEN VAN A"

# Bảng giá mặc định cho từng loại tài khoản (đơn vị: VNĐ / 1 tài khoản)
PRICE_MAP = {
    "gpt": 150000,
    "claude": 200000,
    "gemini": 120000,
    "kiro": 80000
}
DEFAULT_PRICE = 100000
# ========================================================================

bot = telebot.TeleBot(BOT_TOKEN)

# Tên các file lưu trữ dữ liệu cục bộ
ACCOUNTS_FILE = "accounts.txt"
SOLD_FILE = "sold_accounts.txt"

# Bộ nhớ tạm lưu trữ trạng thái đơn hàng của người dùng đang chat
# Cấu trúc: { chat_id: { "category": str, "quantity": int, "order_id": int, "price": int } }
active_orders = {}

# Đảm bảo các file tồn tại
if not os.path.exists(ACCOUNTS_FILE):
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        # Hạt giống tài khoản mẫu nếu file chưa được tạo
        f.write("gpt|chatgpt_user1@gmail.com|pass123|MFA_CODE_001\n")
        f.write("gpt|chatgpt_user2@gmail.com|pass456|MFA_CODE_002\n")
        f.write("claude|claude_user1@gmail.com|pass789|MFA_CODE_003\n")
        f.write("gemini|gemini_user1@gmail.com|passabc|\n")

if not os.path.exists(SOLD_FILE):
    with open(SOLD_FILE, "w", encoding="utf-8") as f:
        pass

def read_accounts():
    """Đọc và lọc các tài khoản khả dụng từ file accounts.txt"""
    accounts = []
    if not os.path.exists(ACCOUNTS_FILE):
        return accounts
    
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 3:
                accounts.append({
                    "category": parts[0].lower(),
                    "username": parts[1],
                    "password": parts[2],
                    "key": parts[3] if len(parts) >= 4 else "",
                    "raw_line": line
                })
    return accounts

def get_stock_counts():
    """Tính số lượng tồn kho cho từng loại tài khoản"""
    accounts = read_accounts()
    counts = {}
    for acc in accounts:
        cat = acc["category"]
        counts[cat] = counts.get(cat, 0) + 1
    return counts

def make_main_keyboard():
    """Tạo bàn phím chính ở dưới chân màn hình chat"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_shop = KeyboardButton("🛒 Mua tài khoản AI")
    btn_history = KeyboardButton("📁 Lịch sử mua hàng")
    btn_help = KeyboardButton("ℹ️ Trợ giúp")
    markup.add(btn_shop, btn_history, btn_help)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🤖 <b>Chào mừng bạn đến với Cửa hàng tài khoản AI tự động!</b>\n\n"
        "Hệ thống bán hàng tự động bằng file lưu trữ độc lập.\n\n"
        "Hãy chọn chức năng bên dưới để bắt đầu giao dịch:"
    )
    bot.send_message(
        message.chat.id, 
        welcome_text, 
        parse_mode="HTML", 
        reply_markup=make_main_keyboard()
    )

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    text = message.text
    chat_id = message.chat.id

    if text == "🛒 Mua tài khoản AI":
        stock = get_stock_counts()
        if not stock:
            bot.send_message(chat_id, "😔 Cửa hàng hiện tại đã hết hàng. Vui lòng quay lại sau.")
            return

        markup = InlineKeyboardMarkup()
        for cat, count in stock.items():
            price = PRICE_MAP.get(cat, DEFAULT_PRICE)
            btn_text = f"{cat.upper()} ({price:,}đ) - Còn {count} cái"
            markup.add(InlineKeyboardButton(text=btn_text, callback_data=f"select_cat_{cat}"))
        
        bot.send_message(chat_id, "👇 Chọn loại tài khoản AI bạn muốn mua:", reply_markup=markup)

    elif text == "📁 Lịch sử mua hàng":
        # Tra cứu từ file sold_accounts.txt các đơn hàng có telegram_id trùng khớp
        history = []
        if os.path.exists(SOLD_FILE):
            with open(SOLD_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = [p.strip() for p in line.split('|')]
                    # Định dạng lưu: timestamp|telegram_id|order_id|category|quantity|price|username|password|key
                    if len(parts) >= 8 and parts[1] == str(chat_id):
                        history.append(parts)

        if not history:
            bot.send_message(chat_id, "📦 Bạn chưa mua tài khoản nào tại đây.")
            return

        bot.send_message(chat_id, f"📅 <b>Lịch sử mua hàng của bạn ({len(history)} tài khoản):</b>", parse_mode="HTML")
        
        # Nhóm theo order_id để hiển thị gọn gàng
        orders_grouped = {}
        for h in history:
            # timestamp, telegram_id, order_id, category, quantity, price, username, password, key
            o_id = h[2]
            if o_id not in orders_grouped:
                orders_grouped[o_id] = {
                    "time": h[0],
                    "category": h[3],
                    "price": int(h[5]),
                    "accounts": []
                }
            orders_grouped[o_id]["accounts"].append({
                "username": h[6],
                "password": h[7],
                "key": h[8] if len(h) >= 9 else ""
            })

        for o_id, o_data in orders_grouped.items():
            acc_list_text = ""
            for idx, acc in enumerate(o_data["accounts"], 1):
                acc_list_text += f" {idx}. User: <code>{html.escape(acc['username'])}</code> | Pass: <code>{html.escape(acc['password'])}</code>"
                if acc["key"]:
                    acc_list_text += f" | MFA Code: <code>{html.escape(acc['key'])}</code>"
                acc_list_text += "\n"

            msg = (
                f"🛍️ <b>Đơn hàng #{o_id}</b> ({o_data['time']})\n"
                f"🏷️ <b>Dịch vụ</b>: {o_data['category'].upper()}\n"
                f"💰 <b>Tổng thanh toán</b>: {o_data['price']:,}đ\n"
                f"🔑 <b>Tài khoản nhận được:</b>\n{acc_list_text}"
                f"---"
            )
            bot.send_message(chat_id, msg, parse_mode="HTML")

    elif text == "ℹ️ Trợ giúp":
        help_msg = (
            "⚙️ <b>Hướng dẫn mua hàng:</b>\n"
            "1. Chọn <b>Mua tài khoản AI</b> ở menu.\n"
            "2. Chọn loại tài khoản và số lượng.\n"
            "3. Chuyển khoản VietQR và click <b>Mô phỏng thanh toán (Test)</b> để nhận tài khoản ngay lập tức.\n\n"
            "💬 Admin hỗ trợ: @admin_username"
        )
        bot.send_message(chat_id, help_msg, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    callback_data = call.data

    # A. Chọn Loại tài khoản -> Chọn số lượng
    if callback_data.startswith("select_cat_"):
        cat = callback_data.replace("select_cat_", "")
        
        stock = get_stock_counts()
        count = stock.get(cat, 0)
        
        if count == 0:
            bot.answer_callback_query(call.id, "❌ Loại tài khoản này hiện đã hết hàng!", show_alert=True)
            return

        bot.delete_message(chat_id, call.message.message_id)

        # Inline button chọn nhanh số lượng
        markup = InlineKeyboardMarkup()
        # Chỉ hiển thị các lựa chọn số lượng phù hợp với số lượng còn trong kho
        for q in [1, 2, 3, 5]:
            if q <= count:
                markup.add(InlineKeyboardButton(text=f"Mua {q} tài khoản", callback_data=f"order_{cat}_{q}"))
        
        bot.send_message(chat_id, f"Chọn số lượng bạn muốn mua cho <b>{cat.upper()}</b>:", parse_mode="HTML", reply_markup=markup)

    # B. Đặt hàng: order_<category>_<quantity>
    elif callback_data.startswith("order_"):
        parts = callback_data.split("_")
        cat = parts[1]
        qty = int(parts[2])

        stock = get_stock_counts()
        count = stock.get(cat, 0)

        if qty > count:
            bot.answer_callback_query(call.id, f"❌ Kho hàng chỉ còn {count} tài khoản!", show_alert=True)
            return

        price_per_acc = PRICE_MAP.get(cat, DEFAULT_PRICE)
        total_price = price_per_acc * qty
        order_id = random.randint(100000, 999999)

        # Lưu đơn hàng tạm thời vào bộ nhớ
        active_orders[chat_id] = {
            "category": cat,
            "quantity": qty,
            "order_id": order_id,
            "price": total_price
        }

        bot.delete_message(chat_id, call.message.message_id)

        # Sinh mã QR VietQR thanh toán
        memo = f"ITBLOG PAY {order_id}"
        qr_url = f"https://img.vietqr.io/image/{BANK_ID}-{BANK_ACCOUNT_NO}-compact2.jpg?amount={total_price}&addInfo={memo}&accountName={BANK_ACCOUNT_NAME}"

        msg = (
            f"🛒 <b>Đơn hàng #{order_id} chờ thanh toán!</b>\n"
            f"📦 <b>Dịch vụ</b>: {cat.upper()}\n"
            f"🔢 <b>Số lượng</b>: {qty} tài khoản\n"
            f"💰 <b>Tổng số tiền</b>: <code>{total_price:,}đ</code>\n"
            f"🔤 <b>Nội dung chuyển khoản bắt buộc</b>: <code>{memo}</code>\n\n"
            f"👉 Vui lòng quét mã QR thanh toán bên dưới. Sau đó nhấn nút 'Mô phỏng thanh toán' để nhận tài khoản ngay lập tức."
        )

        markup = InlineKeyboardMarkup()
        btn_confirm = InlineKeyboardButton("✅ Xác nhận chuyển khoản", callback_data=f"confirm_{order_id}")
        btn_simulate = InlineKeyboardButton("⚡ Mô phỏng thanh toán (Test)", callback_data=f"simulate_{order_id}")
        btn_cancel = InlineKeyboardButton("❌ Hủy đơn", callback_data=f"cancel_{order_id}")
        markup.add(btn_confirm)
        markup.add(btn_simulate)
        markup.add(btn_cancel)

        bot.send_photo(chat_id, qr_url, caption=msg, parse_mode="HTML", reply_markup=markup)

    # C. Mô phỏng thanh toán thành công -> Lấy ngẫu nhiên tài khoản và cập nhật file
    elif callback_data.startswith("simulate_"):
        order_id = int(callback_data.replace("simulate_", ""))
        
        # Kiểm tra đơn hàng có tồn tại trong bộ nhớ tạm
        order = active_orders.get(chat_id)
        if not order or order["order_id"] != order_id:
            bot.answer_callback_query(call.id, "❌ Đơn hàng không tồn tại hoặc đã bị hết hạn.", show_alert=True)
            return

        bot.answer_callback_query(call.id, "🔄 Đang xử lý cấp tài khoản...")

        cat = order["category"]
        qty = order["quantity"]

        # Đọc toàn bộ tài khoản
        all_accounts = read_accounts()
        # Lọc các tài khoản thuộc danh mục được chọn
        matching_accounts = [acc for acc in all_accounts if acc["category"] == cat]

        if len(matching_accounts) < qty:
            bot.send_message(chat_id, "❌ Rất tiếc, kho hàng vừa hết tài khoản khả dụng. Giao dịch đã bị hủy.")
            active_orders.pop(chat_id, None)
            return

        # Lấy ngẫu nhiên tài khoản theo số lượng cần mua
        selected_accounts = random.sample(matching_accounts, qty)
        selected_raw_lines = [acc["raw_line"] for acc in selected_accounts]

        # Cập nhật lại file accounts.txt (Loại bỏ các tài khoản đã bán)
        remaining_lines = []
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line_strip = line.strip()
                    if line_strip and line_strip not in selected_raw_lines:
                        remaining_lines.append(line)

        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            f.writelines(remaining_lines)

        # Lưu thông tin đã bán vào file sold_accounts.txt để làm lịch sử
        timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        with open(SOLD_FILE, "a", encoding="utf-8") as f:
            for acc in selected_accounts:
                # Định dạng: timestamp|telegram_id|order_id|category|quantity|price|username|password|key
                f.write(f"{timestamp}|{chat_id}|{order_id}|{cat}|{qty}|{order['price']}|{acc['username']}|{acc['password']}|{acc['key']}\n")

        # Tạo văn bản tài khoản bàn giao cho khách
        acc_text = ""
        for idx, acc in enumerate(selected_accounts, 1):
            acc_text += f" {idx}. User: <code>{html.escape(acc['username'])}</code> | Pass: <code>{html.escape(acc['password'])}</code>"
            if acc["key"]:
                acc_text += f" | MFA Code: <code>{html.escape(acc['key'])}</code>"
            acc_text += "\n"

        bot.delete_message(chat_id, call.message.message_id)

        success_msg = (
            f"🎉 <b>THANH TOÁN THÀNH CÔNG!</b>\n\n"
            f"🔑 <b>Tài khoản AI của bạn:</b>\n"
            f"{acc_text}\n"
            f"Lưu ý: Bạn có thể xem lại tài khoản bất kỳ lúc nào qua nút <b>📁 Lịch sử mua hàng</b>."
        )
        bot.send_message(chat_id, success_msg, parse_mode="HTML")

        # Xóa khỏi hàng đợi đơn hàng
        active_orders.pop(chat_id, None)

    # D. Hủy đơn hàng
    elif callback_data.startswith("cancel_"):
        bot.delete_message(chat_id, call.message.message_id)
        bot.send_message(chat_id, "❌ Đơn hàng của bạn đã được hủy bỏ thành công.")
        active_orders.pop(chat_id, None)

    # E. Xác nhận chuyển khoản
    elif callback_data.startswith("confirm_"):
        order_id = int(callback_data.replace("confirm_", ""))
        bot.answer_callback_query(call.id, "Ghi nhận thanh toán")
        bot.delete_message(chat_id, call.message.message_id)
        bot.send_message(
            chat_id,
            f"✅ <b>Đã gửi yêu cầu kiểm tra giao dịch #{order_id}!</b>\n\n"
            f"Admin sẽ đối soát chuyển khoản ngân hàng và gửi tài khoản qua tin nhắn sớm nhất."
        )
        active_orders.pop(chat_id, None)

if __name__ == '__main__':
    print("Bot đang khởi động ở chế độ File-Based độc lập...")
    try:
        bot.remove_webhook()
        bot.infinity_polling()
    except Exception as e:
        print(f"Lỗi polling: {e}")
