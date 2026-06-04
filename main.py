import os
import time
import subprocess
import requests
from DrissionPage import ChromiumPage, ChromiumOptions

# --- 配置区 ---
URL = "https://g4f.gg/fgmfurni"
TARGET_HOURS = 72
MAX_LOOPS = 20

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_tg_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("TG 环境变量未配置，跳过发送消息。")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"TG 消息发送失败: {e}")

def get_current_ip():
    try:
        return requests.get('https://api.ipify.org', timeout=5).text
    except:
        return "获取失败"

def rotate_warp_ip(old_ip):
    max_retries = 3
    for i in range(max_retries):
        subprocess.run(['warp-cli', '--accept-tos', 'disconnect'], stdout=subprocess.DEVNULL)
        time.sleep(2)
        subprocess.run(['warp-cli', '--accept-tos', 'connect'], stdout=subprocess.DEVNULL)

        time.sleep(8) 
        new_ip = get_current_ip()

        if new_ip == "获取失败" or new_ip == old_ip:
            continue

        print(f"更换 IP 成功: {new_ip}")
        return new_ip

    return get_current_ip()

def get_current_hours(time_text):
    if not time_text:
        return -1
    try:
        parts = time_text.split(':')
        if len(parts) >= 1:
            return int(parts[0])
    except:
        pass
    return -1

def solve_turnstile(page):
    print("🛡️ 尝试处理 Turnstile 挑战...")
    try:
        target_iframe = page.get_frame('css:iframe[src^="https://challenges.cloudflare.com"]', timeout=5)
        if not target_iframe: 
            print("未检测到 Turnstile 挑战。")
            return False
        time.sleep(2)
        try:
            sr = target_iframe.ele('tag:body').shadow_root
            if sr:
                target_ele = sr.ele('css:input[type="checkbox"]') or sr.ele('css:div.main-wrapper')
                if target_ele:
                    target_ele.click.at(offset_x=10, offset_y=10)
        except: 
            try: 
                target_iframe.frame_ele.click.at(offset_x=30, offset_y=30)
            except: pass

        for _ in range(15):
            time.sleep(1)
            resp = page.ele('css:[name="cf-turnstile-response"]', timeout=1)
            if resp and len(resp.value) > 10: 
                print("✅ Turnstile 验证通过")
                return True
        return False
    except: 
        return False

def main():
    co = ChromiumOptions().auto_port()
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')

    page = ChromiumPage(co)
    page.set.timeouts(page_load=15)

    loop_count = 0
    success_count = 0
    current_ip = get_current_ip()
    print(f"初始运行 IP: {current_ip}")

    while loop_count < MAX_LOOPS:
        loop_count += 1
        print(f"\n--- 第 {loop_count}/{MAX_LOOPS} 次循环 ---")

        try:
            page.get(URL)
        except Exception:
            pass 

        countdown_ele = page.ele('#countdown', timeout=10)

        if not countdown_ele:
            print("页面数据未加载，尝试更换 IP...")
            current_ip = rotate_warp_ip(current_ip)
            continue

        current_time_text = countdown_ele.text
        current_hours = get_current_hours(current_time_text)
        print(f"当前剩余时间: {current_time_text}")

        if current_hours >= TARGET_HOURS:
            print(f"✅ 已达到目标 ({TARGET_HOURS}h)，准备退出。")
            break

        btn = page.ele('.vote-btn')
        if not btn or not btn.states.is_enabled:
            print("按钮冷却或 IP 受限，尝试更换 IP...")
            current_ip = rotate_warp_ip(current_ip)
            continue

        try:
            btn.click(by_js=True)
            print("已发送点击指令...")

            solve_turnstile(page)

            time.sleep(5)

            try:
                page.get(URL)
            except Exception:
                pass

            new_countdown_ele = page.ele('#countdown', timeout=10)
            if new_countdown_ele:
                new_time_text = new_countdown_ele.text

                if current_time_text != new_time_text:
                    print(f"🎉 续期成功！时间更新为 {new_time_text}")
                    success_count += 1
                    current_ip = rotate_warp_ip(current_ip) 
                else:
                    print("时间未改变，更换 IP 重试...")
                    current_ip = rotate_warp_ip(current_ip)
            else:
                print("无法获取刷新后数据，更换 IP...")
                current_ip = rotate_warp_ip(current_ip)

        except Exception as e:
            print(f"点击执行异常: {e}")
            current_ip = rotate_warp_ip(current_ip)

    final_time = "获取失败"
    expiry_info = "获取失败"
    try:
        final_time = page.ele('#countdown').text
        expiry_info = page.ele('.countdown-sub').text
    except:
        pass

    page.quit()

    report_msg = (
        f"🎮 <b>G4F-US 服务器续期任务报告</b>\n"
        f"--------------------------\n"
        f"🔄 循环尝试: {loop_count} / {MAX_LOOPS}\n"
        f"✅ 成功续期: {success_count} 次\n"
        f"⏳ 当前时长: <code>{final_time}</code>\n"
        f"📅 到期信息: {expiry_info}\n"
    )
    send_tg_message(report_msg)
    print("任务执行完毕。")

if __name__ == '__main__':
    main()
