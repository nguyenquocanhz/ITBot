# -*- coding: utf-8 -*-
# Công cụ quản lý kho tài khoản mã hóa (accounts.py)
# Hỗ trợ Xem kho, Nhập tay hoặc Nhập hàng loạt từ file khotaikhoan.txt vào tệp mã hóa accounts.dat.

import os
import base64
import html
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet

DAT_FILE = "accounts.dat"
IMPORT_FILE = "khotaikhoan.txt"

# ==================== CẤU HÌNH MẬT KHẨU MÃ HÓA ====================
# Đảm bảo mật khẩu này khớp với mật khẩu trong bot.py
PASSWORD = "nqatech"
# ==================================================================

def get_fernet(password: str, salt: bytes) -> Fernet:
    """Tạo đối tượng Fernet từ mật khẩu và muối salt bằng PBKDF2"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return Fernet(key)

def decrypt_data(password: str) -> str:
    """Giải mã file accounts.dat sang chuỗi văn bản thuần"""
    if not os.path.exists(DAT_FILE):
        return ""
    with open(DAT_FILE, "rb") as f:
        data = f.read()
    if len(data) < 16:
        return ""
    salt = data[:16]
    encrypted_payload = data[16:]
    try:
        fernet = get_fernet(password, salt)
        decrypted = fernet.decrypt(encrypted_payload)
        return decrypted.decode("utf-8")
    except Exception:
        print("❌ Lỗi: Mật khẩu giải mã không chính xác hoặc dữ liệu bị hỏng!")
        return None

def encrypt_data(password: str, plaintext: str):
    """Mã hóa chuỗi văn bản và ghi đè vào file accounts.dat"""
    salt = os.urandom(16)
    fernet = get_fernet(password, salt)
    encrypted_payload = fernet.encrypt(plaintext.encode("utf-8"))
    with open(DAT_FILE, "wb") as f:
        f.write(salt + encrypted_payload)

def show_stock(content: str):
    """Hiển thị số lượng tồn kho thực tế"""
    if not content:
        print("📭 Kho hiện tại đang trống.")
        return
    
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
            
    print("\n📊 --- THỐNG KÊ TỒN KHO ---")
    for cat, count in stock.items():
        print(f"🔹 {cat.upper()}: {count} tài khoản")
    print("---------------------------\n")

def main():
    print("==============================================")
    print("🔐 HỆ THỐNG QUẢN LÝ KHO TÀI KHOẢN MÃ HÓA (DAT) 🔐")
    print("==============================================")
    
    # Xác thực mật khẩu
    input_pass = input("🔑 Nhập mật khẩu quản trị: ").strip()
    if input_pass != PASSWORD:
        print("❌ Sai mật khẩu. Chương trình kết thúc.")
        return

    # Thử giải mã để kiểm tra tệp tin có hợp lệ không
    content = decrypt_data(PASSWORD)
    if content is None:
        return

    while True:
        print("1. Xem tồn kho & danh sách tài khoản")
        print("2. Nhập tay tài khoản mới")
        print("3. Nhập tự động từ file khotaikhoan.txt")
        print("4. Thoát")
        
        choice = input("👉 Chọn chức năng (1-4): ").strip()
        
        if choice == "1":
            content = decrypt_data(PASSWORD)
            show_stock(content)
            if content:
                print("Chi tiết tài khoản trong kho:")
                lines = content.strip().split("\n")
                for idx, line in enumerate(lines, 1):
                    parts = line.split("|")
                    if len(parts) >= 3:
                        mfa = parts[3] if len(parts) >= 4 else ""
                        print(f" {idx}. [{parts[0].upper()}] User: {parts[1]} | Pass: {parts[2]}" + (f" | MFA: {mfa}" if mfa else ""))
            print()

        elif choice == "2":
            print("\nNhập tài khoản mới theo định dạng: loại tài khoản|username|password|MFA Code")
            print("Gõ 'DONE' và ấn Enter để hoàn thành.")
            new_lines = []
            while True:
                line = input("> ").strip()
                if line.upper() == "DONE":
                    break
                if not line:
                    continue
                parts = line.split("|")
                if len(parts) < 3:
                    print("⚠️ Dòng sai định dạng (thiếu loại, user hoặc pass), vui lòng nhập lại.")
                    continue
                new_lines.append(line)
            
            if new_lines:
                current_content = decrypt_data(PASSWORD)
                updated_content = (current_content + "\n" + "\n".join(new_lines)).strip()
                encrypt_data(PASSWORD, updated_content)
                print(f"✅ Đã thêm thành công {len(new_lines)} tài khoản vào accounts.dat!\n")

        elif choice == "3":
            if not os.path.exists(IMPORT_FILE):
                print(f"❌ Không tìm thấy file '{IMPORT_FILE}' trong thư mục. Vui lòng tạo file này trước.\n")
                continue
            
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
                current_content = decrypt_data(PASSWORD)
                updated_content = (current_content + "\n" + "\n".join(new_lines)).strip()
                encrypt_data(PASSWORD, updated_content)
                
                # Đổi tên file để tránh nạp trùng
                os.rename(IMPORT_FILE, "khotaikhoan_imported.txt")
                print(f"✅ Nhập kho thành công {len(new_lines)} tài khoản từ khotaikhoan.txt!")
                print(f"Tệp khotaikhoan.txt đã được đổi tên thành khotaikhoan_imported.txt để bảo mật.\n")
            else:
                print("⚠️ File khotaikhoan.txt không chứa dữ liệu hợp lệ.\n")

        elif choice == "4":
            print("Chương trình kết thúc.")
            break
        else:
            print("⚠️ Lựa chọn không hợp lệ, vui lòng chọn lại.\n")

if __name__ == '__main__':
    main()
