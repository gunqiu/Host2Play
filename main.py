import os
import sys
import time
import random
import shutil
import requests
import tempfile
import urllib3

from xvfbwrapper import Xvfb
from DrissionPage import ChromiumPage, ChromiumOptions

try:
    import speech_recognition as sr
    from pydub import AudioSegment
except ImportError:
    pass

urllib3.disable_warnings()

# ==============================================================================
# Telegram 通知模块
# ==============================================================================
def send_tg_message(token, chat_id, message):
    if not token or not chat_id:
        print("⚠️ 未配置 TG_TOKEN 或 TG_CHAT_ID，跳过通知")
        return

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        requests.post(url, json=payload, timeout=15)

        print("✅ Telegram 通知发送成功")

    except Exception as e:
        print(f"❌ Telegram 通知失败: {e}")


# ==============================================================================
# reCAPTCHA 音频破解模块
# ==============================================================================
class RecaptchaAudioSolver:

    def __init__(self, page, proxy_url=None):
        self.page = page
        self.proxy_url = proxy_url
        self.log_func = print

    def log(self, msg):
        self.log_func(f"[Solver] {msg}")

    def human_type(self, ele, text):

        ele.click()

        time.sleep(random.uniform(0.2, 0.5))

        ele.clear()

        for char in text:
            ele.input(char, clear=False)
            time.sleep(random.uniform(0.08, 0.25))

        time.sleep(random.uniform(0.5, 1.0))

    def get_audio_source(self, bframe):

        try:

            link1 = bframe.ele(
                '.rc-audiochallenge-ndownload-link',
                timeout=1
            )

            if link1:
                return link1.attr('href')

            link2 = bframe.ele(
                'xpath://a[contains(@href, ".mp3")]',
                timeout=1
            )

            if link2:
                return link2.attr('href')

            audio_src = bframe.ele('#audio-source', timeout=1)

            if audio_src:
                return audio_src.attr('src')

            return None

        except:
            return None

    def solve(self, bframe):

        self.log("🎧 启动音频验证码破解")

        try:

            audio_btn = bframe.ele(
                '#recaptcha-audio-button',
                timeout=5
            )

            if not audio_btn:
                self.log("❌ 未找到音频按钮")
                return False

            self.page.actions.move_to(
                audio_btn,
                duration=random.uniform(0.5, 1.2)
            )

            time.sleep(random.uniform(0.3, 0.6))

            audio_btn.click()

            self.log("🖱️ 已点击音频按钮")

            time.sleep(random.uniform(4, 7))

            src = None

            for attempt in range(3):

                src = self.get_audio_source(bframe)

                if src:
                    break

                self.log(f"⚠️ 第 {attempt+1} 次获取音频失败")

                reload_btn = bframe.ele(
                    '#recaptcha-reload-button',
                    timeout=2
                )

                if reload_btn:

                    reload_btn.click()

                    time.sleep(random.uniform(5, 8))

            if not src:
                self.log("❌ 无法获取音频链接")
                return False

            self.log("📥 下载音频")

            proxies = None

            if self.proxy_url:

                proxies = {
                    "http": self.proxy_url,
                    "https": self.proxy_url
                }

            r = requests.get(
                src,
                timeout=20,
                proxies=proxies,
                verify=False
            )

            with open("audio.mp3", "wb") as f:
                f.write(r.content)

            self.log("🎵 转码 MP3 -> WAV")

            sound = AudioSegment.from_mp3("audio.mp3")

            sound.export("audio.wav", format="wav")

            recognizer = sr.Recognizer()

            with sr.AudioFile("audio.wav") as source:

                audio_data = recognizer.record(source)

                try:

                    key_text = recognizer.recognize_google(audio_data)

                    self.log(f"🗣️ 识别结果: {key_text}")

                except Exception as e:

                    self.log(f"❌ Google 识别失败: {e}")

                    return False

            input_box = bframe.ele('#audio-response', timeout=3)

            if not input_box:
                return False

            self.human_type(input_box, key_text)

            verify_btn = bframe.ele(
                '#recaptcha-verify-button',
                timeout=3
            )

            if verify_btn:

                self.page.actions.move_to(
                    verify_btn,
                    duration=random.uniform(0.5, 1.0)
                )

                time.sleep(random.uniform(0.3, 0.6))

                verify_btn.click()

                self.log("🚀 提交验证码")

                time.sleep(5)

                err = bframe.ele(
                    '.rc-audiochallenge-error-message',
                    timeout=1
                )

                if err and err.states.is_displayed:

                    self.log(f"❌ 验证失败: {err.text}")

                    return False

                self.log("✅ 音频验证码通过")

                return True

            return False

        except Exception as e:

            self.log(f"💥 异常: {e}")

            return False

        finally:

            for f in ["audio.mp3", "audio.wav"]:

                if os.path.exists(f):

                    try:
                        os.remove(f)
                    except:
                        pass


# ==============================================================================
# 主逻辑
# ==============================================================================
def renew_host2play(url, proxy_url=None):

    print("🖥️ 启动 Xvfb")

    vdisplay = Xvfb(
        width=1280,
        height=720,
        colordepth=24
    )

    vdisplay.start()

    success = False
    msg = ""
    page = None

    try:

        co = ChromiumOptions()

        chrome_path = shutil.which("google-chrome") \
            or shutil.which("google-chrome-stable") \
            or "/usr/bin/google-chrome"

        co.set_browser_path(chrome_path)

        # 浏览器参数
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-dev-shm-usage')
        co.set_argument('--disable-gpu')
        co.set_argument('--disable-setuid-sandbox')
        co.set_argument('--disable-software-rasterizer')
        co.set_argument('--disable-extensions')
        co.set_argument('--disable-popup-blocking')
        co.set_argument('--disable-quic')
        co.set_argument('--no-first-run')
        co.set_argument('--no-default-browser-check')

        co.set_argument('--window-size=1280,720')

        # User-Agent
        co.set_user_agent(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/137.0.0.0 Safari/537.36'
        )

        # 用户目录
        user_data_dir = tempfile.mkdtemp()

        co.set_user_data_path(user_data_dir)

        co.auto_port()

        # 无头模式
        co.headless(True)

        # 代理
        if proxy_url:

            print(f"🌐 使用代理: {proxy_url}")

            co.set_argument(
                f'--proxy-server={proxy_url}'
            )

            # 防 DNS 泄漏
            co.set_argument(
                '--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE localhost'
            )

        page = ChromiumPage(co)

        print("🛡️ 注入浏览器伪装")

        page.add_init_js("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3]
            });

            const getParameter =
                WebGLRenderingContext.prototype.getParameter;

            WebGLRenderingContext.prototype.getParameter =
                function(parameter) {

                if (parameter === 37445)
                    return 'Intel Inc.';

                if (parameter === 37446)
                    return 'Intel Iris OpenGL Engine';

                return getParameter.apply(this, [parameter]);
            };
        """)

        # ==============================================================================
        # 测试代理出口
        # ==============================================================================
        print("🧪 测试浏览器出口 IP")

        page.get("https://ip.sb")

        time.sleep(5)

        print(page.html)

        # ==============================================================================
        # 打开续期页面
        # ==============================================================================
        print(f"🌐 打开续期页面: {url}")

        page.get(url, retry=3)

        time.sleep(random.uniform(6, 10))

        # ==============================================================================
        # 清广告
        # ==============================================================================
        print("🧹 清理页面元素")

        page.run_js("""
            const selectors = [
                'ins.adsbygoogle',
                'iframe[src*="ads"]',
                '.modal-backdrop'
            ];

            selectors.forEach(sel => {
                document.querySelectorAll(sel)
                    .forEach(el => el.remove());
            });
        """)

        time.sleep(2)

        # ==============================================================================
        # 模拟人类行为
        # ==============================================================================
        print("🤸 模拟人类行为")

        for _ in range(3):

            page.scroll.down(random.randint(200, 700))

            time.sleep(random.uniform(1, 2))

            page.actions.move(
                random.randint(100, 800),
                random.randint(100, 500)
            )

            time.sleep(random.uniform(0.5, 1.2))

        # ==============================================================================
        # 点击 Renew server
        # ==============================================================================
        print("🖱️ 点击 Renew server")

        renew_btn1 = page.ele(
            'xpath://button[contains(text(), "Renew server")]',
            timeout=5
        )

        if renew_btn1:

            try:
                renew_btn1.click()

            except:
                renew_btn1.click(by_js=True)

        else:

            page.run_js("""
                document.querySelectorAll('button')
                .forEach(btn => {
                    if (btn.innerText.includes('Renew server')) {
                        btn.click();
                    }
                });
            """)

        time.sleep(5)

        # ==============================================================================
        # 等待弹窗
        # ==============================================================================
        for _ in range(10):

            if page.ele('text:Expires in:', timeout=1):
                break

            if page.ele('text:Deletes on:', timeout=1):
                break

            time.sleep(1)

        # ==============================================================================
        # 第二次点击 Renew server
        # ==============================================================================
        renew_btn2 = page.ele(
            'xpath://button[contains(text(), "Renew server")]',
            timeout=3
        )

        if renew_btn2:

            try:
                renew_btn2.click()

            except:
                renew_btn2.click(by_js=True)

        time.sleep(random.uniform(7, 10))

        # ==============================================================================
        # reCAPTCHA
        # ==============================================================================
        solved_captcha = False

        anchor_frame = page.get_frame(
            'xpath://iframe[contains(@src, "recaptcha/api2/anchor")]',
            timeout=10
        )

        if anchor_frame:

            print("✅ 已发现 reCAPTCHA")

            anchor_box = None

            for _ in range(20):

                anchor_box = anchor_frame.ele(
                    '#recaptcha-anchor',
                    timeout=1
                )

                if anchor_box:
                    break

                time.sleep(1)

            if not anchor_box:

                msg = "❌ reCAPTCHA checkbox 超时"

                return success, msg

            print("🖱️ 点击 reCAPTCHA")

            page.actions.move_to(
                anchor_box,
                duration=random.uniform(0.5, 1.5)
            )

            time.sleep(random.uniform(0.3, 0.7))

            anchor_box.click()

            time.sleep(random.uniform(5, 8))

            checked = anchor_box.attr('aria-checked')

            if checked == 'true':

                print("✅ reCAPTCHA 自动通过")

                solved_captcha = True

            else:

                print("🎲 进入音频验证")

                bframe = page.get_frame(
                    'xpath://iframe[contains(@src, "recaptcha/api2/bframe")]',
                    timeout=10
                )

                if bframe:

                    solver = RecaptchaAudioSolver(
                        page,
                        proxy_url
                    )

                    solved_captcha = solver.solve(bframe)

        else:

            msg = "❌ 未发现 reCAPTCHA"

        # ==============================================================================
        # 最终 Renew
        # ==============================================================================
        if solved_captcha:

            print("🚀 点击最终 Renew")

            final_btn = page.ele(
                'xpath://button[normalize-space(text())="Renew"]',
                timeout=5
            )

            if final_btn:

                try:
                    final_btn.click()

                except:
                    final_btn.click(by_js=True)

                time.sleep(10)

                success = True

                msg = "🎉 host2play 续期成功"

            else:

                msg = "❌ 未找到最终 Renew 按钮"

        else:

            if not msg:
                msg = "❌ reCAPTCHA 未通过"

    except Exception as e:

        msg = f"💥 异常: {str(e)[:300]}"

        print(msg)

    finally:

        if page:

            try:
                page.quit()
            except:
                pass

        try:
            vdisplay.stop()
        except:
            pass

        return success, msg


# ==============================================================================
# 入口
# ==============================================================================
if __name__ == "__main__":

    renew_url = os.getenv("RENEW_URL")

    tg_token = os.getenv("TG_TOKEN")

    tg_chat_id = os.getenv("TG_CHAT_ID")

    proxy_url = os.getenv(
        "PROXY",
        "socks5://127.0.0.1:10808"
    )

    if not renew_url:

        print("❌ 缺少 RENEW_URL")

        sys.exit(1)

    print("======================================")
    print("🚀 Host2Play 自动续期启动")
    print("======================================")

    print(f"🔗 续期链接: {renew_url}")

    print(f"🌐 代理: {proxy_url}")

    success, result = renew_host2play(
        renew_url,
        proxy_url
    )

    print(result)

    send_tg_message(
        tg_token,
        tg_chat_id,
        result
    )

    if not success:
        sys.exit(1)

    sys.exit(0)
```
