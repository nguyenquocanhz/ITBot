# -*- coding: utf-8 -*-
# Trình quản lý TUI thông minh cho Telegram Bot (manage.py)
# Giao diện TUI tương tác bằng phím mũi tên điều hướng, chạy không cần thư viện bên ngoài.

import os
import sys
import msvcrt
import base64
import html
import random
import time
import subprocess
from datetime import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet

DAT_FILE = "accounts.dat"
SOLD_FILE = "sold_accounts.txt"
IMPORT_FILE = "khotaikhoan.txt"
PASSWORD = "nqatech"  # Mật khẩu đồng bộ mã hóa

# Định nghĩa mã màu ANSI cho giao diện TUI
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_CYAN = "\033[96m"
COLOR_REVERSE = "\033[7m"

def clear_screen():
    os.system('cls')

def get_fernet(password: str, salt: bytes) -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return Fernet(key)

def decrypt_data() -> str:
    if not os.path.exists(DAT_FILE):
        return ""
    with open(DAT_FILE, "rb") as f:
        data = f.read()
    if len(data) < 16:
        return ""
    salt = data[:16]
    encrypted_payload = data[16:]
    try:
        fernet = get_fernet(PASSWORD, salt)
        decrypted = fernet.decrypt(encrypted_payload)
        return decrypted.decode("utf-8")
    except Exception:
        return None

def encrypt_data(plaintext: str):
    salt = os.urandom(16)
    fernet = get_fernet(PASSWORD, salt)
    encrypted_payload = fernet.encrypt(plaintext.encode("utf-8"))
    with open(DAT_FILE, "wb") as f:
        f.write(salt + encrypted_payload)

def get_stock_counts():
    content = decrypt_data()
    if not content:
        return {}
    lines = content.strip().split("\n")
    stock = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) >= 3:
            cat = parts[0].strip().lower()
            stock[cat] = stock.get(cat, 0) + 1
    return stock

def draw_header():
    print(COLOR_CYAN + COLOR_BOLD)
    print(" ┌────────────────────────────────────────────────────────┐")
    print(" │         🤖 ITBOT CONTROL PANEL - STANDALONE TUI        │")
    print(" └────────────────────────────────────────────────────────┘" + COLOR_RESET)

def draw_menu(options, selected_idx):
    draw_header()
    
    # Hiển thị nhanh số lượng hàng hiện tại trong kho
    stock = get_stock_counts()
    print(" TỒN KHO HIỆN TẠI:")
    if not stock:
        print(COLOR_YELLOW + "   [ Kho đang trống - Vui lòng nạp thêm ]" + COLOR_RESET)
    else:
        for cat, count in stock.items():
            print(f"   • {cat.upper()}: {COLOR_GREEN}{count}{COLOR_RESET} tài khoản")
    print(" ──────────────────────────────────────────────────────────")
    
    print(" CHỌN CHỨC NĂNG (Dùng phím ↑ ↓ và Enter để chọn):\n")
    
    for idx, opt in enumerate(options):
        if idx == selected_idx:
            print(COLOR_REVERSE + f"  ▶  {opt}  " + COLOR_RESET)
        else:
            print(f"     {opt}")
            
    print("\n ──────────────────────────────────────────────────────────")

def read_key():
    ch = msvcrt.getch()
    if ch in (b'\x00', b'\xe0'):
        ch = msvcrt.getch()
        if ch == b'H': return "up"
        if ch == b'P': return "down"
    elif ch == b'\r':
        return "enter"
    return None

def show_all_accounts():
    clear_screen()
    draw_header()
    content = decrypt_data()
    if content is None:
        print(COLOR_RED + "❌ Lỗi giải mã file accounts.dat" + COLOR_RESET)
    elif not content.strip():
        print(COLOR_YELLOW + "📭 Kho hàng trống." + COLOR_RESET)
    else:
        print(" DANH SÁCH CHI TIẾT TÀI KHOẢN TRONG KHO:")
        lines = content.strip().split("\n")
        for idx, line in enumerate(lines, 1):
            parts = line.split("|")
            if len(parts) >= 3:
                mfa = parts[3] if len(parts) >= 4 else ""
                print(f" {COLOR_CYAN}{idx:02d}.{COLOR_RESET} [{COLOR_GREEN}{parts[0].upper()}{COLOR_RESET}] User: {parts[1]} | Pass: {parts[2]}" + (f" | MFA: {mfa}" if mfa else ""))
    
    print("\nẤn phím bất kỳ để quay lại menu...")
    msvcrt.getch()

def add_accounts_manually():
    clear_screen()
    draw_header()
    print(" NHẬP TÀI KHOẢN THỦ CÔNG")
    print(" Định dạng nhập: loại tài khoản|username|password|MFA Code")
    print(" Gõ 'DONE' và ấn Enter để lưu.\n")
    
    new_lines = []
    while True:
        line = input("> ").strip()
        if line.upper() == "DONE":
            break
        if not line:
            continue
        parts = line.split("|")
        if len(parts) < 3:
            print(COLOR_YELLOW + "⚠️  Dòng sai định dạng (Thiếu loại, user hoặc pass), nhập lại." + COLOR_RESET)
            continue
        new_lines.append(line)
        
    if new_lines:
        current_content = decrypt_data()
        if current_content is not None:
            updated_content = (current_content + "\n" + "\n".join(new_lines)).strip()
            encrypt_data(updated_content)
            print(COLOR_GREEN + f"\n✅ Đã lưu thành công {len(new_lines)} tài khoản mới vào accounts.dat!" + COLOR_RESET)
        else:
            print(COLOR_RED + "❌ Lỗi: Không thể lưu dữ liệu." + COLOR_RESET)
    else:
        print("\nHủy nhập tài khoản.")
        
    time.sleep(1.5)

def import_from_txt():
    clear_screen()
    draw_header()
    print(" NHẬP KHO HÀNG LOẠT TỪ FILE khotaikhoan.txt")
    
    if not os.path.exists(IMPORT_FILE):
        print(COLOR_RED + f"\n❌ Không tìm thấy file '{IMPORT_FILE}'." + COLOR_RESET)
        print("Vui lòng tạo file này và đặt cùng thư mục với manage.py.")
    else:
        with open(IMPORT_FILE, "r", encoding="utf-8") as f:
            import_content = f.read()
            
        new_lines = []
        for line in import_content.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) >= 3:
                new_lines.append(line)
                
        if new_lines:
            current_content = decrypt_data()
            if current_content is not None:
                updated_content = (current_content + "\n" + "\n".join(new_lines)).strip()
                encrypt_data(updated_content)
                os.rename(IMPORT_FILE, "khotaikhoan_imported.txt")
                print(COLOR_GREEN + f"\n✅ Nhập kho thành công {len(new_lines)} tài khoản từ khotaikhoan.txt!" + COLOR_RESET)
                print("Đã đổi tên tệp nguồn thành khotaikhoan_imported.txt để bảo mật.")
            else:
                print(COLOR_RED + "❌ Lỗi nạp dữ liệu vào accounts.dat." + COLOR_RESET)
        else:
            print(COLOR_YELLOW + "\n⚠️  Tệp khotaikhoan.txt không chứa dòng dữ liệu hợp lệ." + COLOR_RESET)
            
    print("\nẤn phím bất kỳ để quay lại menu...")
    msvcrt.getch()

def view_sales_history():
    clear_screen()
    draw_header()
    if not os.path.exists(SOLD_FILE) or os.path.getsize(SOLD_FILE) == 0:
        print(COLOR_YELLOW + "📭 Lịch sử bán hàng đang trống." + COLOR_RESET)
    else:
        print(" LỊCH SỬ TÀI KHOẢN ĐÃ BÁN (sold_accounts.txt):\n")
        with open(SOLD_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("|")
                # format: timestamp|telegram_id|order_id|category|quantity|price|username|password|key
                if len(parts) >= 8:
                    mfa = parts[8] if len(parts) >= 9 else ""
                    print(f" 📅 [{parts[0]}] ĐH #{parts[2]} | Khách: {parts[1]}")
                    print(f"    ↳ [{parts[3].upper()}] User: {parts[6]} | Pass: {parts[7]}" + (f" | MFA: {mfa}" if mfa else ""))
                    print("-" * 55)
                    
    print("\nẤn phím bất kỳ để quay lại menu...")
    msvcrt.getch()

def launch_bot():
    clear_screen()
    draw_header()
    print(" ĐANG KHỞI ĐỘNG TELEGRAM BOT...")
    print("Hệ thống sẽ mở một cửa sổ console mới để chạy Bot.py.")
    
    try:
        # Sử dụng lệnh start cmd để mở cửa sổ CMD mới chạy bot.py trên Windows
        subprocess.Popen("start cmd /k python bot.py", shell=True)
        print(COLOR_GREEN + "\n✅ Đã phát lệnh chạy bot.py trong cửa sổ console mới!" + COLOR_RESET)
        print("Bạn có thể xem nhật ký chạy và tương tác của bot ở cửa sổ mới đó.")
    except Exception as e:
        print(COLOR_RED + f"\n❌ Không thể khởi động bot: {e}" + COLOR_RESET)
        
    time.sleep(2.5)

def main():
    # Kiểm tra mật khẩu tại màn hình TUI ban đầu
    clear_screen()
    draw_header()
    print(" 🛡️  HỆ THỐNG YÊU CẦU XÁC THỰC MẬT KHẨU")
    
    attempts = 0
    while True:
        passwd = input("   👉 Nhập mật khẩu quản trị: ").strip()
        if passwd == PASSWORD:
            break
        attempts += 1
        print(COLOR_RED + f"   ❌ Sai mật khẩu! Vui lòng thử lại. (Lần nhập sai: {attempts})" + COLOR_RESET)
        print()

    options = [
        "1. Xem chi tiết kho hàng tài khoản",
        "2. Nhập thêm tài khoản thủ công (Nhập tay)",
        "3. Nhập tự động từ file khotaikhoan.txt",
        "4. Xem lịch sử bán hàng (Đơn hàng đã giao)",
        "5. Khởi động Telegram Bot (Mở console riêng)",
        "6. Thoát chương trình"
    ]
    
    selected_idx = 0
    
    while True:
        clear_screen()
        draw_menu(options, selected_idx)
        
        key = read_key()
        if key == "up":
            selected_idx = (selected_idx - 1) % len(options)
        elif key == "down":
            selected_idx = (selected_idx + 1) % len(options)
        elif key == "enter":
            if selected_idx == 0:
                show_all_accounts()
            elif selected_idx == 1:
                add_accounts_manually()
            elif selected_idx == 2:
                import_from_txt()
            elif selected_idx == 3:
                view_sales_history()
            elif selected_idx == 4:
                launch_bot()
            elif selected_idx == 5:
                clear_screen()
                print("Tạm biệt!")
                break

if __name__ == '__main__':
    # Hỗ trợ hiển thị bảng màu ANSI trên CMD của Windows
    os.system('')
    main()
