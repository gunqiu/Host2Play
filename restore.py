import os
import time
import random
from datetime import datetime
from seleniumbase import SB

USERNAME = os.getenv("MAGMA_USERNAME")
PASSWORD = os.getenv("MAGMA_PASSWORD")

BASE_URL = "https://magmanode.com/login"

SCREENSHOT_DIR = "scripts/screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def ts():
    return int(time.time())


def shot(sb, name):
    path = f"{SCREENSHOT_DIR}/{name}_{ts()}.png"
    sb.save_screenshot(path)
    print(f"📸 screenshot: {path}")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def find_and_type(sb, selectors, value):
    """多 selector 容错输入"""
    for sel in selectors:
        try:
            sb.type(sel, value, timeout=5)
            return True
        except Exception:
            continue
    raise Exception(f"无法找到输入框: {selectors}")


def click_any(sb, selectors):
    """多策略点击"""
    for sel in selectors:
        try:
            sb.click(sel, timeout=5)
            return True
        except Exception:
            continue
    raise Exception(f"无法点击元素: {selectors}")


def detect_status(page_text):
    t = page_text.lower()
    if "offline" in t:
        return "Offline"
    if "starting" in t:
        return "Starting"
    if "online" in t:
        return "Online"
    return "Unknown"


with SB(uc=True, test=True, locale_code="en") as sb:

    for attempt in range(1, 4):
        log(f"🔁 尝试 {attempt}/3")

        try:
            # =========================
            # 1. 打开登录页
            # =========================
            log("🌍 打开登录")
            sb.open(BASE_URL)
            time.sleep(3)
            shot(sb, "login_page")

            # =========================
            # 2. 输入账号密码（增强兼容）
            # =========================
            log("✏️ 填写账户")

            find_and_type(sb, [
                'input[name="email"]',
                'input[type="email"]',
                'input[placeholder*="email" i]',
                '#email'
            ], USERNAME)

            find_and_type(sb, [
                'input[name="password"]',
                'input[type="password"]',
                '#password'
            ], PASSWORD)

            shot(sb, "filled")

            # =========================
            # 3. 登录
            # =========================
            log("🔐 点击登录")
            click_any(sb, [
                "text=Login",
                "text=Sign in",
                "button[type=submit]",
                "input[type=submit]"
            ])

            time.sleep(6)
            shot(sb, "after_login")

            # =========================
            # 4. 服务页
            # =========================
            log("📊 检查服务")
            page_text = sb.get_page_source()
            shot(sb, "services")

            # =========================
            # 5. Manage
            # =========================
            log("🖱️ 打开管理")

            click_any(sb, [
                "text=Manage",
                "//a[contains(text(),'Manage')]",
                "//button[contains(text(),'Manage')]"
            ])

            time.sleep(5)
            shot(sb, "console")

            # =========================
            # 6. 状态检测
            # =========================
            status = detect_status(sb.get_page_source())
            log(f"🖥️ 状态 = {status}")

            if status == "Offline":
                log("▶️ 点击 START")
                click_any(sb, [
                    "text=Start",
                    "text=START",
                    "button=Start"
                ])

            # =========================
            # 7. 轮询
            # =========================
            for i in range(12):
                time.sleep(5)
                status = detect_status(sb.get_page_source())
                log(f"⏳ {i+1}/12 => {status}")

                if status in ["Starting", "Online"]:
                    break

            shot(sb, "final")
            log("🎉 完成")

            break

        except Exception as e:
            log(f"❌ 失败: {e}")
            shot(sb, f"error_attempt_{attempt}")
            time.sleep(3)
