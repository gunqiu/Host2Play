import os
import sys
import time
import random
import html
import requests
import tempfile
from xvfbwrapper import Xvfb
from DrissionPage import ChromiumPage, ChromiumOptions

try:
    import speech_recognition as sr
    from pydub import AudioSegment
except ImportError:
    pass

# ========================= 配置区域 =========================
RENEW_URLS = [
    "https://host2play.gratis/server/renew?i=d4f4f701-8302-4050-b89d-29492027ccfd",
]

MAX_CAPTCHA = 4
MAX_RENEW_RETRIES_PER_URL = 8
PROXY_NODE = ""

# ============================================================

class CaptchaBlocked(Exception):
    pass

def log(msg, level="INFO"):
    print(f"[{level}] {msg}", flush=True)

# ========================= TG 通知 =========================
def send_tg_photo(token, chat_id, photo_path, caption):
    if not token or not chat_id or not photo_path or not os.path.exists(photo_path):
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        with open(photo_path, "rb") as f:
            requests.post(url, data={
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "HTML"
            }, files={"photo": f}, timeout=20)
    except Exception as e:
        log(f"TG 通知失败: {e}", "WARN")

# ========================= 页面获取 =========================
def get_server_name(page):
    try:
        return page.ele("#serverName", timeout=2).text.strip()
    except:
        return "Unknown"

def get_expire_time(page):
    try:
        return page.ele("#expireDate", timeout=2).text.strip()
    except:
        try:
            e = page.ele("text:Expires in:", timeout=1)
            if e:
                return e.text.split(":", 1)[1].strip()
        except:
            pass
    return "Unknown"

# ========================= 验证码核心 =========================
def find_recaptcha_frame(page, kind):
    try:
        for f in page.get_frames():
            if "recaptcha" in f.url and kind in f.url:
                return f
    except:
        pass
    return None

def is_recaptcha_solved(page):
    try:
        for f in page.get_frames():
            t = f.run_js('return document.querySelector("textarea[name=g-recaptcha-response]")?.value')
            if t and len(t) > 30:
                return True
    except:
        pass
    return False

def click_recaptcha_checkbox(page):
    f = find_recaptcha_frame(page, "anchor")
    if f:
        f.ele("#recaptcha-anchor", timeout=3).click(by_js=True)
        time.sleep(2)

def switch_to_audio(page):
    f = find_recaptcha_frame(page, "bframe")
    if not f:
        return False
    try:
        f.ele("#recaptcha-audio-button").click(by_js=True)
        time.sleep(2)
        return True
    except:
        return False

def get_audio_url(page):
    f = find_recaptcha_frame(page, "bframe")
    if f:
        return f.ele(".rc-audiochallenge-tdownload-link").attr("href")
    return None

def recognize_audio(mp3):
    try:
        wav = mp3.replace(".mp3", ".wav")
        AudioSegment.from_mp3(mp3).export(wav, format="wav")
        r = sr.Recognizer()
        with sr.AudioFile(wav) as s:
            text = r.recognize_google(r.record(s), language="en-US")
        os.remove(wav)
        return text.strip().lower()
    except:
        return None

def fill_and_verify(page, text):
    f = find_recaptcha_frame(page, "bframe")
    if f:
        f.ele("#audio-response").input(text)
        time.sleep(1)
        f.ele("#recaptcha-verify-button").click(by_js=True)
        time.sleep(4)

def solve_recaptcha(page):
    click_recaptcha_checkbox(page)
    if is_recaptcha_solved(page):
        return

    for _ in range(2):
        if switch_to_audio(page):
            break
        time.sleep(2)

    url = get_audio_url(page)
    if not url:
        raise Exception("获取音频地址失败")

    mp3 = tempfile.mktemp(suffix=".mp3")
    with open(mp3, "wb") as f:
        f.write(requests.get(url, timeout=15).content)

    text = recognize_audio(mp3)
    os.remove(mp3)

    if text:
        fill_and_verify(page, text)

# ========================= 单个续期 =========================
def renew_single(url):
    success = False
    server = "Unknown"
    old_expire = "Unknown"
    new_expire = "Unknown"
    screenshot = None
    reason = ""

    vdisplay = Xvfb(width=1280, height=720)
    vdisplay.start()

    try:
        for attempt in range(MAX_RENEW_RETRIES_PER_URL):
            page = None
            try:
                co = ChromiumOptions()
                co.set_browser_path("/usr/bin/google-chrome")
                co.set_argument("--no-sandbox")
                co.set_argument("--disable-dev-shm-usage")
                co.set_argument("--disable-gpu")
                co.set_argument("--disable-blink-features=AutomationControlled")
                co.set_argument("--window-size=1280,720")
                co.headless(False)
                co.auto_port()
                co.set_user_data_path(tempfile.mkdtemp())

                page = ChromiumPage(co)
                page.get(url, retry=2)
                time.sleep(random.uniform(4, 6))

                server = get_server_name(page)
                old_expire = get_expire_time(page)
                log(f"服务器: {server} | 到期: {old_expire}")

                # 打开续期弹窗
                page.run_js('document.querySelectorAll("button").forEach(b=>{if(b.innerText.includes("Renew"))b.click()})')
                time.sleep(random.uniform(4, 6))

                # 处理验证码
                if find_recaptcha_frame(page, "anchor"):
                    solve_recaptcha(page)

                # 点击最终续期按钮
                page.run_js('document.querySelectorAll("button").forEach(b=>{if(b.innerText==="Renew")b.click()})')
                time.sleep(random.uniform(6, 8))

                new_expire = get_expire_time(page)
                if new_expire != old_expire:
                    success = True

                break

            except Exception as e:
                reason = str(e)[:150]
                log(f"第 {attempt+1} 次失败: {reason}")
                if page:
                    page.quit()
                continue

        # 保存截图
        os.makedirs("output/screenshots", exist_ok=True)
        screenshot = f"output/screenshots/{server}_{'ok' if success else 'fail'}.png"
        if page:
            page.get_screenshot(screenshot)
            page.quit()

    except Exception as e:
        reason = str(e)[:150]

    finally:
        vdisplay.stop()

    return success, server, old_expire, new_expire, screenshot, reason

# ========================= 主入口（修复了解包错误） =========================
def main():
    tg_token = os.getenv("TG_BOT_TOKEN")
    tg_chat = os.getenv("TG_CHAT_ID")

    for url in RENEW_URLS:
        log(f"开始处理: {url}")
        # 修复解包错误：和 return 的 6 个值一一对应
        ok, name, old, new, pic, reason = renew_single(url)

        if ok:
            text = f"✅ 续期成功\n服务器: {name}\n到期: {old} → {new}"
        else:
            text = f"❌ 续期失败\n原因: {reason}"

        send_tg_photo(tg_token, tg_chat, pic, text)
        time.sleep(2)

if __name__ == "__main__":
    main()
