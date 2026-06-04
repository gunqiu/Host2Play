import os
import time
import requests
from datetime import datetime
from seleniumbase import SB

# ======================
# 配置
# ======================
USERNAME = os.getenv("MAGMA_USERNAME")
PASSWORD = os.getenv("MAGMA_PASSWORD")

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

MAX_RETRY = int(os.getenv("MAX_RETRY", "3"))

TARGET_URL = "https://magmanode.com/login"
SCREENSHOT_DIR = "scripts/screenshots"


# ======================
# 工具函数
# ======================
def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    print(f"[{now()}] {msg}", flush=True)


def send_tg(text=None, image=None):
    if not TG_TOKEN or not TG_CHAT_ID:
        return

    try:
        if text:
            requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                data={"chat_id": TG_CHAT_ID, "text": text},
                timeout=10,
            )

        if image:
            with open(image, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto",
                    data={"chat_id": TG_CHAT_ID},
                    files={"photo": f},
                    timeout=20,
                )
    except Exception as e:
        log(f"❌ TG 发送失败: {e}")


def shot(sb, name):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    path = f"{SCREENSHOT_DIR}/{name}_{int(time.time())}.png"
    sb.save_screenshot(path)
    log(f"📸 screenshot: {path}")
    return path


# ======================
# 主流程
# ======================
def run_once():
    with SB(uc=True, test=True, xvfb=True) as sb:
        log("🌍 opening page...")
        sb.open(TARGET_URL)

        shot(sb, "after_login")

        # ======================
        # 输入账号密码
        # ======================
        try:
            sb.type('input[name="email"]', USERNAME)
            sb.type('input[name="password"]', PASSWORD)
            log("✏️ account/password filled")
        except Exception as e:
            log(f"❌ fill error: {e}")

        shot(sb, "filled_form")

        # ======================
        # 点击登录
        # ======================
        try:
            sb.click('button[type="submit"]')
            log("🔐 clicking login")
        except:
            sb.click("text=Sign in")

        time.sleep(6)

        shot(sb, "after_login_click")

        # ======================
        # 判断是否进入 services
        # ======================
        if "services" in sb.get_current_url():
            log("✅ login success -> services page")
        else:
            log("⚠️ login state uncertain, continue anyway")

        shot(sb, "services_page")

        # ======================
        # 点击 Manage
        # ======================
        try:
            sb.click("text=Manage")
            log("🖱️ clicked Manage")
        except Exception as e:
            log(f"❌ Manage click failed: {e}")
            return

        time.sleep(4)

        shot(sb, "console_page")

        # ======================
        # 判断服务器状态
        # ======================
        status_text = sb.get_page_source()

        if "Offline" in status_text:
            log("🖥️ server is Offline -> clicking START")

            try:
                sb.click("text=START")
            except:
                sb.click("button=Start")

            log("▶️ START clicked")

        else:
            log("🖥️ server already running")

        # ======================
        # 轮询状态
        # ======================
        for i in range(12):
            time.sleep(5)
            page = sb.get_page_source()

            if "Starting" in page:
                log(f"⏳ polling {i+1}/12: Starting")
            elif "Online" in page:
                log(f"✅ server Online at attempt {i+1}")
                break

        final_shot = shot(sb, "final")

        send_tg("🎉 Magmanode restore completed")
        send_tg(image=final_shot)


# ======================
# 重试机制
# ======================
def main():
    for i in range(MAX_RETRY):
        try:
            log(f"🔁 attempt {i+1}/{MAX_RETRY}")
            run_once()
            return
        except Exception as e:
            log(f"❌ failed: {e}")
            time.sleep(5)

    log("❌ all attempts failed")


if __name__ == "__main__":
    main()
