import os
import time
import re
import requests
from datetime import datetime
from seleniumbase import SB

# ======================
# ENV
# ======================
USERNAME = os.getenv("MAGMA_USERNAME")
PASSWORD = os.getenv("MAGMA_PASSWORD")

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

MAX_RETRY = int(os.getenv("MAX_RETRY", "3"))

LOGIN_URL = "https://magmanode.com/login"
SCREEN_DIR = "scripts/screenshots"


# ======================
# LOG
# ======================
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ======================
# TG
# ======================
def tg(msg=None, img=None):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        if msg:
            requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                data={"chat_id": TG_CHAT_ID, "text": msg},
                timeout=10,
            )
        if img:
            with open(img, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto",
                    data={"chat_id": TG_CHAT_ID},
                    files={"photo": f},
                    timeout=20,
                )
    except Exception as e:
        log(f"TG error: {e}")


# ======================
# screenshot
# ======================
def shot(sb, name):
    os.makedirs(SCREEN_DIR, exist_ok=True)
    path = f"{SCREEN_DIR}/{name}_{int(time.time())}.png"
    sb.save_screenshot(path)
    log(f"📸 {path}")
    return path


# ======================
# SAFE CLICK（核心）
# ======================
def click(sb, keywords):
    """
    统一点击策略（成功版本核心）
    """
    for k in keywords:
        try:
            sb.click(f"text={k}")
            log(f"🖱️ click text={k}")
            return True
        except:
            pass

        try:
            sb.click(f"xpath=//*[contains(.,'{k}')]")
            log(f"🖱️ click xpath={k}")
            return True
        except:
            pass

    return False


# ======================
# SAFE TYPE（核心）
# ======================
def type_any(sb, value):
    """
    不依赖 selector，直接扫 input
    """
    try:
        inputs = sb.find_elements("input")
        for i in inputs:
            try:
                i.click()
                i.clear()
                i.send_keys(value)
                return True
            except:
                continue
    except:
        pass
    return False


# ======================
# STATUS ENGINE（成功版本关键）
# ======================
def get_status(sb):
    src = sb.get_page_source().lower()

    if "online" in src:
        return "online"
    if "starting" in src:
        return "starting"
    if "offline" in src:
        return "offline"

    return "unknown"


# ======================
# MAIN FLOW
# ======================
def run_once():

    with SB(uc=True, test=True, xvfb=True) as sb:

        # ============= LOGIN
        log("🌍 open login")
        sb.open(LOGIN_URL)
        time.sleep(3)

        shot(sb, "login_page")

        log("✏️ fill account")
        type_any(sb, USERNAME)
        type_any(sb, PASSWORD)

        shot(sb, "filled")

        log("🔐 login click")
        click(sb, ["Sign in", "Login", "Log in"])
        time.sleep(6)

        shot(sb, "after_login")

        # ============= SERVICES
        log("📊 check services")

        if "services" in sb.get_current_url():
            log("✅ login OK")

        shot(sb, "services")

        # ============= MANAGE
        log("🖱️ open manage")

        click(sb, ["Manage", "manage"])
        time.sleep(5)

        shot(sb, "console")

        # ============= STATUS
        status = get_status(sb)
        log(f"🖥️ status = {status}")

        if status == "offline":
            log("▶️ start server")
            click(sb, ["START", "Start"])
        else:
            log("🟢 already running")

        # ============= POLLING LOOP（成功版本核心）
        for i in range(12):
            time.sleep(5)

            status = get_status(sb)
            log(f"⏳ {i+1}/12 => {status}")

            if status == "online":
                log("🟢 ONLINE CONFIRMED")
                break

        final = shot(sb, "final")

        tg("restore completed")
        tg(img=final)


# ======================
# RETRY WRAPPER
# ======================
def main():
    for i in range(MAX_RETRY):
        try:
            log(f"🔁 attempt {i+1}/{MAX_RETRY}")
            run_once()
            return
        except Exception as e:
            log(f"❌ error: {e}")
            time.sleep(5)

    log("❌ all failed")


if __name__ == "__main__":
    main()
