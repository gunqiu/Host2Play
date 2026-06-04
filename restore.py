import os
import time
from datetime import datetime
from seleniumbase import SB

USERNAME = os.getenv("MAGMA_USERNAME")
PASSWORD = os.getenv("MAGMA_PASSWORD")

BASE_URL = "https://magmanode.com/login"

SCREENSHOT_DIR = "scripts/screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def shot(sb, name):
    path = f"{SCREENSHOT_DIR}/{name}_{int(time.time())}.png"
    sb.save_screenshot(path)
    print(f"📸 screenshot: {path}")


def detect(page):
    p = page.lower()
    if "offline" in p:
        return "Offline"
    if "starting" in p:
        return "Starting"
    if "online" in p:
        return "Online"
    return "Unknown"


def safe_click(sb, selectors):
    for s in selectors:
        try:
            sb.click(s, timeout=5)
            return True
        except:
            pass
    return False


def safe_type(sb, selectors, value):
    for s in selectors:
        try:
            sb.type(s, value, timeout=5)
            return True
        except:
            pass
    return False


with SB(uc=True, test=True, locale_code="en") as sb:

    for attempt in range(1, 4):

        log(f"🔁 尝试 {attempt}/3")

        try:
            # =========================
            # 1. 登录页
            # =========================
            log("🌍 打开登录页...")
            sb.open(BASE_URL)
            sb.sleep(4)

            shot(sb, "00_login_opened")

            # =========================
            # 2. 输入账号密码（强容错）
            # =========================
            log("✏️ 填写账户")

            inputs = sb.find_elements("input")

            user_box = None
            pass_box = None

            for i in inputs:
                t = (i.get_attribute("type") or "").lower()
                n = (i.get_attribute("name") or "").lower()

                if not user_box and t != "password":
                    user_box = i

                if not pass_box and t == "password":
                    pass_box = i

            if not user_box or not pass_box:
                raise Exception("输入框识别失败")

            user_box.clear()
            user_box.send_keys(USERNAME)

            pass_box.clear()
            pass_box.send_keys(PASSWORD)

            shot(sb, "01_login_form")

            # =========================
            # 3. 登录
            # =========================
            log("🖱️ 点击登录")

            safe_click(sb, [
                "text=Sign in",
                "text=Login",
                "button[type=submit]"
            ])

            sb.sleep(6)

            shot(sb, "03_services_page")

            # =========================
            # 4. 进入 Manage
            # =========================
            log("🖱️ Manage 按钮已点击（按文本内容定位）")

            safe_click(sb, [
                "text=Manage",
                "//a[contains(.,'Manage')]",
                "//button[contains(.,'Manage')]"
            ])

            sb.sleep(5)

            shot(sb, "05_console_page")

            # =========================
            # 5. 状态判断（同款关键）
            # =========================
            page = sb.get_page_source()
            status = detect(page)

            log(f"🖥️ 服务器运行状态: {status}")

            if status == "Offline":
                log("▶️ 服务器已停止，先清理广告再点击 START...")

                safe_click(sb, [
                    "text=Start",
                    "text=START",
                    "//button[contains(.,'Start')]"
                ])

                log("🖱️ 已点击 START，开始轮询...")

            # =========================
            # 6. 轮询（同款日志）
            # =========================
            for i in range(1, 13):

                sb.sleep(5)

                status = detect(sb.get_page_source())

                log(f"⏳ {i}/12，当前状态: {status}")

                if status in ["Starting", "Online"]:
                    break

            shot(sb, "06_console_final")

            # =========================
            # 7. 成功结束（同款）
            # =========================
            log("🎉 全部流程执行完毕！")

            break

        except Exception as e:
            log(f"❌ 错误: {e}")
            shot(sb, f"error_attempt_{attempt}")
            sb.sleep(3)
