```python
import os
import sys
import time
import random
import shutil
import requests
import tempfile

from xvfbwrapper import Xvfb
from DrissionPage import ChromiumPage, ChromiumOptions

try:
    import speech_recognition as sr
    from pydub import AudioSegment
except:
    pass

# ==============================================================================
# 全局代理
# ==============================================================================
PROXY = os.getenv("PROXY", "http://127.0.0.1:8080")

GLOBAL_PROXIES = {
    "http": PROXY,
    "https": PROXY
}

# ==============================================================================
# Telegram 通知
# ==============================================================================
def send_tg_message(token, chat_id, message):
    if not token or not chat_id:
        print("⚠️ 未配置 TG_TOKEN 或 TG_CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        requests.post(
            url,
            json=payload,
            proxies=GLOBAL_PROXIES,
            timeout=20
        )

        print("✅ Telegram 通知成功")

    except Exception as e:
        print(f"❌ Telegram 通知失败: {e}")

# ==============================================================================
# reCAPTCHA 音频破解器
# ==============================================================================
class RecaptchaAudioSolver:

    def __init__(self, page):
        self.page = page

    def log(self, msg):
        print(f"[Solver] {msg}")

    def human_type(self, ele, text):

        ele.click()
        time.sleep(random.uniform(0.2, 0.5))

        ele.clear()

        for c in text:
            ele.input(c, clear=False)
            time.sleep(random.uniform(0.08, 0.22))

        time.sleep(random.uniform(0.5, 1.2))

    def get_audio_source(self, bframe):

        selectors = [
            '.rc-audiochallenge-tdownload-link',
            '.rc-audiochallenge-tdownload-link',
            '#audio-source',
            'xpath://a[contains(@href, ".mp3")]'
        ]

        for s in selectors:
            try:
                ele = bframe.ele(s, timeout=1)

                if ele:
                    src = ele.attr('href') or ele.attr('src')

                    if src:
                        return src

            except:
                pass

        return None

    def solve(self, bframe):

        self.log("🎧 开始音频破解")

        try:

            audio_btn = bframe.ele('#recaptcha-audio-button', timeout=5)

            if not audio_btn:
                self.log("❌ 未找到音频按钮")
                return False

            self.page.actions.move_to(
                audio_btn,
                duration=random.uniform(0.5, 1.5)
            )

            time.sleep(random.uniform(0.5, 1.0))

            audio_btn.click()

            self.log("🖱️ 已点击音频按钮")

            time.sleep(random.uniform(4, 7))

            audio_src = None

            for i in range(5):

                audio_src = self.get_audio_source(bframe)

                if audio_src:
                    break

                self.log(f"⚠️ 第 {i+1} 次获取音频失败")

                reload_btn = bframe.ele(
                    '#recaptcha-reload-button',
                    timeout=2
                )

                if reload_btn:
                    reload_btn.click()

                time.sleep(random.uniform(4, 7))

            if not audio_src:
                self.log("❌ 无法获取音频")
                return False

            self.log("📥 下载音频")

            r = requests.get(
                audio_src,
                proxies=GLOBAL_PROXIES,
                timeout=30
            )

            with open("audio.mp3", "wb") as f:
                f.write(r.content)

            try:

                audio = AudioSegment.from_mp3("audio.mp3")

                audio.export(
                    "audio.wav",
                    format="wav"
                )

            except Exception as e:
                self.log(f"❌ ffmpeg 转码失败: {e}")
                return False

            recognizer = sr.Recognizer()

            with sr.AudioFile("audio.wav") as source:

                audio_data = recognizer.record(source)

                try:

                    text = recognizer.recognize_google(
                        audio_data
                    )

                    self.log(f"🗣️ 识别结果: {text}")

                except Exception as e:
                    self.log(f"❌ Google Speech 失败: {e}")
                    return False

            input_box = bframe.ele(
                '#audio-response',
                timeout=5
            )

            if not input_box:
                self.log("❌ 找不到输入框")
                return False

            self.human_type(input_box, text)

            verify_btn = bframe.ele(
                '#recaptcha-verify-button',
                timeout=5
            )

            if not verify_btn:
                self.log("❌ 找不到 Verify 按钮")
                return False

            self.page.actions.move_to(
                verify_btn,
                duration=random.uniform(0.5, 1.0)
            )

            time.sleep(random.uniform(0.2, 0.5))

            verify_btn.click()

            self.log("🚀 提交验证")

            time.sleep(random.uniform(5, 8))

            err = bframe.ele(
                '.rc-audiochallenge-error-message',
                timeout=1
            )

            if err and err.states.is_displayed:
                self.log(f"❌ 验证失败: {err.text}")
                return False

            return True

        except Exception as e:

            self.log(f"💥 音频破解异常: {e}")

            return False

        finally:

            for f in ["audio.mp3", "audio.wav"]:
                if os.path.exists(f):
                    os.remove(f)

# ==============================================================================
# Host2Play 续期
# ==============================================================================
def renew_host2play(url):

    print("🖥️ 启动虚拟桌面")

    vdisplay = Xvfb(
        width=1366,
        height=768,
        colordepth=24
    )

    vdisplay.start()

    page = None
    success = False
    message = ""

    user_data_dir = tempfile.mkdtemp()

    try:

        co = ChromiumOptions()

        co.set_browser_path('/usr/bin/google-chrome')

        co.set_argument('--no-sandbox')
        co.set_argument('--disable-dev-shm-usage')
        co.set_argument('--disable-gpu')
        co.set_argument('--disable-blink-features=AutomationControlled')
        co.set_argument('--disable-setuid-sandbox')
        co.set_argument('--disable-infobars')
        co.set_argument('--disable-popup-blocking')
        co.set_argument('--window-size=1366,768')
        co.set_argument('--lang=en-US')

        co.set_argument(f'--proxy-server={PROXY}')

        co.set_user_agent(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/136.0.0.0 Safari/537.36'
        )

        co.set_user_data_path(user_data_dir)

        co.auto_port()

        co.headless(False)

        print("🚀 启动 Chromium")

        page = ChromiumPage(co)

        print("🛡️ 注入反检测脚本")

        page.add_init_js("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4]
            });

            const getParameter =
                WebGLRenderingContext.prototype.getParameter;

            WebGLRenderingContext.prototype.getParameter =
                function(parameter) {

                if (parameter === 37445)
                    return 'Intel Inc.';

                if (parameter === 37446)
                    return 'Intel Iris OpenGL Engine';

                return getParameter.call(this, parameter);
            };
        """)

        print("🌐 测试当前出口 IP")

        page.get("https://api.ipify.org")

        ip = page.html

        print(f"✅ 当前 IP: {ip}")

        print(f"🌐 打开续期页面: {url}")

        page.get(
            url,
            retry=3,
            timeout=60
        )

        time.sleep(random.uniform(6, 10))

        print("🤸 模拟真人行为")

        for _ in range(5):

            page.scroll.down(
                random.randint(200, 700)
            )

            time.sleep(random.uniform(0.5, 1.5))

            page.actions.move(
                random.randint(100, 1200),
                random.randint(100, 600)
            )

            time.sleep(random.uniform(0.5, 1.5))

        print("🧹 清理广告元素")

        page.run_js("""
            document.querySelectorAll(
                'iframe,ins,.adsbygoogle,.modal-backdrop'
            ).forEach(e => e.remove());
        """)

        time.sleep(2)

        renew_btn = page.ele(
            'xpath://button[contains(text(),"Renew server")]',
            timeout=8
        )

        if not renew_btn:

            message = "❌ 找不到 Renew server"

            return success, message

        print("🖱️ 点击 Renew server")

        try:
            renew_btn.click()

        except:
            renew_btn.click(by_js=True)

        time.sleep(random.uniform(5, 8))

        second_btn = page.ele(
            'xpath://button[contains(text(),"Renew server")]',
            timeout=8
        )

        if second_btn:

            try:
                second_btn.click()

            except:
                second_btn.click(by_js=True)

        time.sleep(random.uniform(7, 10))

        print("🔍 查找 reCAPTCHA")

        anchor_frame = page.get_frame(
            'xpath://iframe[contains(@src,"anchor")]',
            timeout=10
        )

        if not anchor_frame:

            page.save(path='error_no_iframe.html')

            message = "❌ 未找到 reCAPTCHA"

            return success, message

        checkbox = anchor_frame.ele(
            '#recaptcha-anchor',
            timeout=10
        )

        if not checkbox:

            message = "❌ 找不到 checkbox"

            return success, message

        print("🖱️ 点击 reCAPTCHA")

        page.actions.move_to(
            checkbox,
            duration=random.uniform(0.5, 1.5)
        )

        time.sleep(random.uniform(0.3, 0.8))

        checkbox.click()

        time.sleep(random.uniform(5, 8))

        checked = checkbox.attr('aria-checked')

        solved = False

        if checked == 'true':

            print("✅ reCAPTCHA 自动通过")

            solved = True

        else:

            print("🎧 进入音频破解")

            bframe = page.get_frame(
                'xpath://iframe[contains(@src,"bframe")]',
                timeout=10
            )

            if bframe:

                solver = RecaptchaAudioSolver(page)

                solved = solver.solve(bframe)

        if not solved:

            page.save(path='error_captcha_failed.html')

            message = "❌ reCAPTCHA 破解失败"

            return success, message

        print("🚀 点击最终 Renew")

        final_btn = page.ele(
            'xpath://button[normalize-space(text())="Renew"]',
            timeout=8
        )

        if not final_btn:

            message = "❌ 找不到最终 Renew"

            return success, message

        try:
            final_btn.click()

        except:
            final_btn.click(by_js=True)

        time.sleep(random.uniform(8, 15))

        success = True

        message = "🎉 Host2Play 续期成功"

        return success, message

    except Exception as e:

        message = f"💥 异常: {str(e)[:300]}"

        print(message)

        return success, message

    finally:

        try:
            if page:
                page.quit()
        except:
            pass

        try:
            vdisplay.stop()
        except:
            pass

        try:
            shutil.rmtree(user_data_dir)
        except:
            pass

# ==============================================================================
# 主程序
# ==============================================================================
if __name__ == "__main__":

    renew_url = os.getenv("RENEW_URL")

    tg_token = os.getenv("TG_TOKEN")

    tg_chat_id = os.getenv("TG_CHAT_ID")

    if not renew_url:

        print("❌ 缺少 RENEW_URL")

        sys.exit(1)

    print("===================================================")
    print("🚀 Host2Play Auto Renew")
    print("===================================================")

    ok, msg = renew_host2play(renew_url)

    print(msg)

    send_tg_message(
        tg_token,
        tg_chat_id,
        msg
    )

    if not ok:
        sys.exit(1)
```
