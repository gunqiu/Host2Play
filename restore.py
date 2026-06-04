import os
import time
import requests
from datetime import datetime
from seleniumbase import SB

# =========================
# 配置
# =========================
USERNAME = os.getenv("MAGMA_USERNAME")
PASSWORD = os.getenv("MAGMA_PASSWORD")

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

MAX_RETRY = int(os.getenv("MAX_RETRY", "3"))

SCREENSHOT_DIR = "scripts/screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

TARGET_URL = "https://magmanode.com/login"  # ← 如果你有真实地址，替换这里


# =========================
# Telegram 推送
# =========================
def tg_send(text):
    if not TG_TOKEN or not TG_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, data={
            "chat_id": TG_CHAT_ID,
            "text": text
        }, timeout=10)
    except Exception as e:
        print("TG send error:", e)


def tg_send_photo(path, caption=""):
    if not TG_TOKEN or not TG_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    try:
        with open(path, "rb") as f:
            requests.post(url, data={
                "chat_id": TG_CHAT_ID,
                "caption": caption
            }, files={"photo": f}, timeout=20)
    except Exception as e:
        print("TG photo error:", e)


# =========================
# 截图
# =========================
def save_shot(sb, name):
    path = f"{SCREENSHOT_DIR}/{name}_{int(time.time())}.png"
    sb.save_screenshot(path)
    print("📸 screenshot:", path)
    return path


# =========================
# 主逻辑
# =========================
def run_once():
    with SB(uc=True, headless=True) as sb:
        print("🌍 opening page...")
        sb.open(TARGET_URL)

        time.sleep(3)

        # ===== 登录 =====
        try:
            sb.type("input[name='username']", USERNAME)
            sb.type("input[name='password']", PASSWORD)
            sb.click("button[type='submit']")
        except Exception:
            print("⚠️ login selectors not matched, skip auto login")

        time.sleep(8)

        save_shot(sb, "after_login")

        # ===== 等待系统状态 =====
        start = time.time()
        while time.time() - start < 120:
            page = sb.get_page_source()

            if "running" in page.lower() or "starting" in page.lower():
                print("✅ system running detected")
                break

            time.sleep(5)

        # 最终截图
        final_path = save_shot(sb, "final")

        tg_send("🎉 Magma Restore 执行完成")
        tg_send_photo(final_path, "restore result")

        return True


# =========================
# 重试机制
# =========================
if __name__ == "__main__":
    tg_send("🚀 Restore task started")

    for i in range(MAX_RETRY):
        print(f"🔁 attempt {i+1}/{MAX_RETRY}")

        try:
            ok = run_once()
            if ok:
                break
        except Exception as e:
            print("❌ error:", e)
            tg_send(f"❌ restore error: {e}")
            time.sleep(5)

    tg_send("🏁 Restore finished")
