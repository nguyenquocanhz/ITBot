# -*- coding: utf-8 -*-
# Telegram Bot bán tài khoản AI (bot.py) sử dụng pyTelegramBotAPI
# Kết nối đồng bộ với Website thông qua cổng API bảo mật.

import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import html

# ==================== CẤU HÌNH BOT TELEGRAM ====================
# Điền Token Bot của bạn tạo từ @BotFather vào đây
BOT_TOKEN = "5552327462:AAE7gPWPzlXwn4zUQRGIp5ezoprmu9ADjkQ"

# URL của website Blog & Shop (Nếu chạy local thì dùng http://127.0.0.1:8000)
WEB_URL = "http://127.0.0.1:8000"

# Khóa API bí mật kết nối Bot và Web (Phải khớp với BOT_API_KEY trong config.php)
BOT_API_KEY = "nqatech"
# ===============================================================

bot = telebot.TeleBot(BOT_TOKEN)
API_ENDPOINT = f"{WEB_URL}/api/bot.php"
HEADERS = {"X-Bot-Key": BOT_API_KEY}

def call_web_api(action, data=None):
    """Hàm phụ gọi Web API an toàn và trả về JSON"""
    if data is None:
        data = {}
    data['action'] = action
    try:
        response = requests.post(API_ENDPOINT, headers=HEADERS, data=data, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"success": False, "message": f"HTTP Error {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}

def make_main_keyboard():
    """Tạo bàn phím chức năng chính dưới màn hình chat"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_shop = KeyboardButton("🛒 Mua tài khoản AI")
    btn_history = KeyboardButton("📁 Lịch sử mua hàng")
    btn_help = KeyboardButton("ℹ️ Trợ giúp")
    markup.add(btn_shop, btn_history, btn_help)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Xử lý lệnh khởi động /start hoặc trợ giúp"""
    welcome_text = (
        "🤖 <b>Chào mừng bạn đến với Cửa hàng tài khoản AI!</b>\n\n"
        "Cửa hàng cung cấp các tài khoản ChatGPT Plus, Claude Pro, Midjourney kích hoạt ngay lập tức.\n\n"
        "Hãy chọn một chức năng dưới đây để bắt đầu mua hàng:"
    )
    bot.send_message(
        message.chat.id, 
        welcome_text, 
        parse_mode="HTML", 
        reply_markup=make_main_keyboard()
    )

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    """Xử lý các tin nhắn từ bàn phím chức năng chính"""
    text = message.text
    chat_id = message.chat.id

    if text == "🛒 Mua tài khoản AI":
        # Gọi API lấy danh sách dịch vụ đang bán
        res = call_web_api("get_services")
        if not res.get("success"):
            bot.send_message(chat_id, f"❌ Không thể tải danh sách dịch vụ: {res.get('message')}")
            return

        services = res.get("services", [])
        if not services:
            bot.send_message(chat_id, "😔 Cửa hàng hiện tại chưa có dịch vụ nào mở bán.")
            return

        # Tạo Inline Buttons để người dùng chọn mua
        markup = InlineKeyboardMarkup()
        for s in services:
            # Chỉ hiển thị nếu còn hàng hoặc hiển thị trạng thái hết hàng
            stock_info = f"Còn {s['stock_count']}" if s['stock_count'] > 0 else "Hết hàng"
            btn_text = f"{s['name']} ({int(s['price']):,}đ) - {stock_info}"
            # Gửi callback data: buy_id_<service_id>
            markup.add(InlineKeyboardButton(text=btn_text, callback_data=f"buy_id_{s['id']}"))

        bot.send_message(chat_id, "👇 Chọn tài khoản AI bạn muốn mua bên dưới:", reply_markup=markup)

    elif text == "📁 Lịch sử mua hàng":
        # Tra cứu các tài khoản đã mua thành công dựa trên Telegram ID
        res = call_web_api("get_history", {"telegram_id": chat_id})
        if not res.get("success"):
            bot.send_message(chat_id, f"❌ Lỗi tra cứu: {res.get('message')}")
            return

        history = res.get("history", [])
        if not history:
            bot.send_message(chat_id, "📦 Bạn chưa mua tài khoản nào. Hãy click '🛒 Mua tài khoản AI' để ủng hộ shop nhé!")
            return

        bot.send_message(chat_id, f"📅 <b>Lịch sử mua hàng của bạn ({len(history)} đơn):</b>", parse_mode="HTML")
        for h in history:
            # Parse thông tin tài khoản giải mã
            try:
                acc_info = json.loads(h['account_data'])
                acc_text = f"User: <code>{html.escape(acc_info.get('username',''))}</code>\nPass: <code>{html.escape(acc_info.get('password',''))}</code>"
                if acc_info.get('key'):
                    acc_text += f"\nMFA Code: <code>{html.escape(acc_info.get('key',''))}</code>"
            except:
                acc_text = f"Thông tin: <code>{html.escape(h['account_data'])}</code>"

            msg = (
                f"🏷️ <b>Dịch vụ</b>: {html.escape(h['service_name'])}\n"
                f"💰 <b>Giá mua</b>: {int(h['price']):,}đ\n"
                f"🔑 <b>Tài khoản bàn giao</b>:\n{acc_text}\n"
                f"---"
            )
            bot.send_message(chat_id, msg, parse_mode="HTML")

    elif text == "ℹ️ Trợ giúp":
        help_msg = (
            "⚙️ <b>Hướng dẫn mua hàng:</b>\n"
            "1. Bấm <b>Mua tài khoản AI</b> dưới menu.\n"
            "2. Chọn loại tài khoản cần mua.\n"
            "3. Quét mã QR chuyển khoản và sao chép đúng nội dung chuyển khoản.\n"
            "4. Chọn <b>Mô phỏng thanh toán (Test)</b> để nhận ngay tài khoản tức thì mà không cần thanh toán tiền thật khi thử nghiệm.\n\n"
            "💬 Liên hệ hỗ trợ trực tuyến: @admin_username"
        )
        bot.send_message(chat_id, help_msg, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    """Xử lý các tương tác nút bấm Inline Keyboard"""
    chat_id = call.message.chat.id
    callback_data = call.data

    # A. Xử lý đặt hàng: buy_id_<service_id>
    if callback_data.startswith("buy_id_"):
        service_id = int(callback_data.replace("buy_id_", ""))
        first_name = call.from_user.first_name or "Telegram User"
        username = call.from_user.username or ""
        telegram_name = f"{first_name} (@{username})" if username else first_name

        # Tạo đơn hàng
        res = call_web_api("create_order", {
            "telegram_id": chat_id,
            "telegram_name": telegram_name,
            "service_id": service_id
        })

        if not res.get("success"):
            if res.get("message") == "out_of_stock":
                bot.answer_callback_query(call.id, "❌ Dịch vụ này đã hết hàng trong kho!", show_alert=True)
            else:
                bot.answer_callback_query(call.id, f"❌ Lỗi: {res.get('message')}", show_alert=True)
            return

        order_id = res['order_id']
        price = res['price']
        qr_url = res['qr_url']
        memo = res['memo']

        # Xóa tin nhắn chọn dịch vụ cũ đi để gọn giao diện
        bot.delete_message(chat_id, call.message.message_id)

        # Gửi thông tin thanh toán kèm ảnh QR VietQR
        msg = (
            f"🛒 <b>Đơn hàng #{order_id} chờ thanh toán!</b>\n"
            f"📦 <b>Dịch vụ</b>: {html.escape(res['service_name'])}\n"
            f"💰 <b>Số tiền cần trả</b>: <code>{int(price):,}đ</code>\n"
            f"🔤 <b>Nội dung chuyển khoản bắt buộc</b>: <code>{html.escape(memo)}</code>\n\n"
            f"👉 Vui lòng quét mã QR chuyển khoản dưới đây. Hệ thống sẽ bàn giao tài khoản ngay sau khi thanh toán thành công."
        )

        markup = InlineKeyboardMarkup()
        btn_confirm = InlineKeyboardButton("✅ Xác nhận chuyển khoản", callback_data=f"confirm_{order_id}")
        btn_simulate = InlineKeyboardButton("⚡ Mô phỏng thanh toán (Test)", callback_data=f"simulate_{order_id}")
        btn_cancel = InlineKeyboardButton("❌ Hủy đơn", callback_data=f"cancel_{order_id}")
        markup.add(btn_confirm)
        markup.add(btn_simulate)
        markup.add(btn_cancel)

        # Gửi QR và tin nhắn thanh toán
        bot.send_photo(chat_id, qr_url, caption=msg, parse_mode="HTML", reply_markup=markup)

    # B. Xử lý giả lập thanh toán: simulate_<order_id>
    elif callback_data.startswith("simulate_"):
        order_id = int(callback_data.replace("simulate_", ""))
        
        # Báo hiệu đang xử lý
        bot.answer_callback_query(call.id, "🔄 Đang kiểm tra thanh toán...")

        res = call_web_api("complete_order", {"order_id": order_id})
        
        if not res.get("success"):
            if res.get("message") == "out_of_stock":
                bot.send_message(chat_id, "❌ Rất tiếc, kho hàng đã hết tài khoản khả dụng. Đơn hàng tự động hủy.")
            else:
                bot.send_message(chat_id, f"❌ Cấp phát tài khoản thất bại: {res.get('message')}")
            return

        # Giải mã tài khoản nhận được
        try:
            acc_info = json.loads(res['account_data'])
            acc_text = f"User: <code>{html.escape(acc_info.get('username',''))}</code>\nPass: <code>{html.escape(acc_info.get('password',''))}</code>"
            if acc_info.get('key'):
                acc_text += f"\nMFA Code: <code>{html.escape(acc_info.get('key',''))}</code>"
        except:
            acc_text = f"Tài khoản: <code>{html.escape(res['account_data'])}</code>"

        # Cập nhật giao diện xóa ảnh QR đi
        bot.delete_message(chat_id, call.message.message_id)

        success_msg = (
            f"🎉 <b>THANH TOÁN THÀNH CÔNG!</b>\n\n"
            f"🔑 <b>Thông tin tài khoản AI của bạn:</b>\n"
            f"{acc_text}\n\n"
            f"Lưu ý: Bạn có thể xem lại tài khoản đã mua bất kỳ lúc nào tại nút <b>📁 Lịch sử mua hàng</b>."
        )
        bot.send_message(chat_id, success_msg, parse_mode="HTML")

    # C. Xác nhận chuyển khoản: confirm_<order_id>
    elif callback_data.startswith("confirm_"):
        order_id = int(callback_data.replace("confirm_", ""))
        bot.answer_callback_query(call.id, "Ghi nhận giao dịch chuyển khoản")
        
        bot.delete_message(chat_id, call.message.message_id)
        
        bot.send_message(
            chat_id,
            f"✅ <b>Đã gửi yêu cầu phê duyệt đơn hàng #{order_id}!</b>\n\n"
            f"Admin sẽ kiểm tra biến động số dư tài khoản ngân hàng và duyệt đơn cấp tài khoản cho bạn sớm nhất (thường là 5-15 phút).",
            parse_mode="HTML"
        )

    # D. Hủy đơn hàng: cancel_<order_id>
    elif callback_data.startswith("cancel_"):
        order_id = int(callback_data.replace("cancel_", ""))
        call_web_api("cancel_order", {"order_id": order_id})
        
        bot.answer_callback_query(call.id, "Đã hủy đơn hàng")
        bot.delete_message(chat_id, call.message.message_id)
        bot.send_message(chat_id, "❌ Đơn hàng của bạn đã được hủy bỏ thành công.")

if __name__ == '__main__':
    print("Bot đang khởi động...")
    try:
        # Xóa Webhook cũ để tránh lỗi Conflict 409 khi chạy Long Polling
        bot.remove_webhook()
        bot.infinity_polling()
    except Exception as e:
        print(f"Lỗi polling: {e}")
