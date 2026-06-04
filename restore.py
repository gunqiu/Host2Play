import os
import time
import requests
from datetime import datetime
from seleniumbase import SB

USERNAME = os.getenv("MAGMA_USERNAME")
PASSWORD = os.getenv("MAGMA_PASSWORD")

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

MAX_RETRY = int(os.getenv("MAX_RETRY", "3"))

TARGET_URL = "https://magmanode.com/login"
SCREENSHOT_DIR = "scripts/screenshots"


# ======================
# log
# ======================
def now():
    return datetime.now().strftime("%H:%M:%S")

def log(msg):
    print(f"[{now()}] {msg}", flush=True)


# ======================
# tg
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
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    path = f"{SCREENSHOT_DIR}/{name}_{int(time.time())}.png"
    sb.save_screenshot(path)
    log(f"📸 {path}")
    return path


# ======================
# 自适应输入（核心）
# ======================
def smart_type(sb, value, label):
    """
    不依赖 selector，自动找 input
    """

    selectors = [
        "input[type='email']",
        "input[type='text']",
        "input[type='password']",
        "input",
    ]

    for sel in selectors:
        try:
            els = sb.find_elements(sel)
            for el in els:
                try:
                    el.click()
                    el.clear()
                    el.send_keys(value)
                    log(f"✏️ {label} -> matched {sel}")
                    return True
                except:
                    continue
        except:
            continue

    log(f"❌ {label} not found")
    return False


# ======================
# 点击按钮（模糊匹配）
# ======================
def smart_click(sb, keywords):
    """
    keywords: list[str]
    """

    try:
        page = sb.get_page_source()
    except:
        page = ""

    for kw in keywords:
        try:
            sb.click(f"text={kw}")
            log(f"🖱️ clicked text={kw}")
            return True
        except:
            pass

        try:
            sb.click(f"xpath=//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{kw.lower()}')]")
            log(f"🖱️ clicked xpath contains {kw}")
            return True
        except:
            pass

    log(f"❌ click failed: {keywords}")
    return False


# ======================
# 主流程
# ======================
def run_once():

    with SB(uc=True, test=True, xvfb=True) as sb:

        log("🌍 open login page")
        sb.open(TARGET_URL)
        time.sleep(3)

        shot(sb, "after_open")

        # ======================
        # 登录输入（稳定版）
        # ======================
        log("✏️ filling credentials")

        smart_type(sb, USERNAME, "username")
        smart_type(sb, PASSWORD, "password")

        shot(sb, "filled")

        # ======================
        # 登录按钮
        # ======================
        log("🔐 login click")

        smart_click(sb, ["Sign in", "Login", "Log in", "Submit"])

        time.sleep(6)

        shot(sb, "after_login")

        # ======================
        # services 判断
        # ======================
        url = sb.get_current_url()
        if "services" in url:
            log("✅ login success")
        else:
            log("⚠️ login uncertain")

        shot(sb, "services")

        # ======================
        # Manage
        # ======================
        log("🖱️ entering manage")

        smart_click(sb, ["Manage", "manage", "Panel", "console"])

        time.sleep(5)

        shot(sb, "console")

        # ======================
        # 状态判断
        # ======================
        page = sb.get_page_source().lower()

        if "offline" in page:
            log("🛑 offline -> start server")

            smart_click(sb, ["START", "Start", "start"])

        else:
            log("🟢 already running")

        # ======================
        # 轮询状态
        # ======================
        for i in range(10):
            time.sleep(5)
            page = sb.get_page_source().lower()

            if "starting" in page:
                log(f"⏳ {i+1}/10 starting")
            if "online" in page:
                log("🟢 online confirmed")
                break

        final = shot(sb, "final")

        tg("restore done")
        tg(img=final)


# ======================
# retry
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
