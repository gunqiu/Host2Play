import os
import time
import random
from DrissionPage import ChromiumPage, ChromiumOptions
from loguru import logger

# ==================== 配置 ====================
RENEW_URL = "https://host2play.gratis/server/renew?i=d4f4f701-8302-4050-b89d-29492027ccfd"
PROXY_SERVER = os.getenv("PROXY_SERVER", "")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.getenv("TG_CHAT_ID", "")
MAX_CAPTCHA = 1
WAIT_TIME = 2
# ==============================================

def send_telegram(msg):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    try:
        import requests
        requests.get(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage?chat_id={TG_CHAT_ID}&text={msg}")
    except:
        pass

def create_browser():
    co = ChromiumOptions()
    co.set_argument("--no-sandbox")
    co.set_argument("--disable-dev-shm-usage")
    co.set_argument("--headless=new")
    co.set_argument("--disable-gpu")
    co.set_argument("--window-size=1920,1080")
    co.set_argument("--disable-blink-features=AutomationControlled")
    co.set_argument("--lang=en-US")
    co.set_timeouts(page_load=30)

    if PROXY_SERVER:
        logger.info(f"✅ 使用代理: {PROXY_SERVER}")
        co.set_argument(f"--proxy-server={PROXY_SERVER}")
    else:
        logger.info("✅ 直连模式")

    page = ChromiumPage(addr_or_opts=co)
    return page

def run():
    page = create_browser()
    try:
        logger.info("🚀 打开续期页面...")
        page.get(RENEW_URL)
        time.sleep(WAIT_TIME + random.uniform(1, 2))

        if page.ele("text=Renew"):
            logger.info("✅ 点击 Renew")
            page.ele("text=Renew").click()
            time.sleep(WAIT_TIME)

        attempt = 0
        while attempt < MAX_CAPTCHA:
            if page.ele(".recaptcha-checkbox-border"):
                logger.info(f"🤖 尝试验证 {attempt+1}")
                page.ele(".recaptcha-checkbox-border").click()
                time.sleep(WAIT_TIME + random.uniform(1, 2))
                attempt += 1
            else:
                break

        if page.ele("text=Success") or page.ele("text=renewed"):
            logger.success("🎉 Host2Play 续期成功！")
            send_telegram("✅ Host2Play 续期成功")
        else:
            logger.warning("⚠️ 续期完成（需手动验证）")
            send_telegram("⚠️ Host2Play 续期需验证")

    except Exception as e:
        logger.error(f"❌ 失败: {str(e)}")
        send_telegram("❌ Host2Play 续期失败")
    finally:
        page.quit()

if __name__ == "__main__":
    run()
