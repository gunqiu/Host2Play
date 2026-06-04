import os
import time
import json
import requests
from datetime import datetime

# =========================
# 环境变量（严格匹配你的 YAML）
# =========================

USERNAME = os.getenv("MAGMA_USERNAME")
PASSWORD = os.getenv("MAGMA_PASSWORD")

TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

MAX_RETRY = int(os.getenv("MAX_RETRY", "3"))

STATUS_URL = os.getenv("STATUS_URL")
RESTORE_URL = os.getenv("RESTORE_URL")

TIMEOUT = 120
CHECK_INTERVAL = 5


# =========================
# TG 通知
# =========================

def tg(msg):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("⚠️ TG 未配置")
        return

    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": TG_CHAT_ID,
            "text": msg
        }, timeout=10)
    except Exception as e:
        print("TG失败:", e)


def tg_photo(path, caption=""):
    if not TG_TOKEN or not TG_CHAT_ID:
        return

    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        with open(path, "rb") as f:
            requests.post(url, data={
                "chat_id": TG_CHAT_ID,
                "caption": caption
            }, files={"photo": f}, timeout=20)
    except Exception as e:
        print("TG图片失败:", e)


# =========================
# 状态请求（关键修复点）
# =========================

def get_status():
    if not STATUS_URL:
        print("❌ STATUS_URL 未设置")
        return {}

    try:
        r = requests.get(STATUS_URL, timeout=10)
        try:
            return r.json()
        except:
            print("⚠️ 状态不是JSON:", r.text[:200])
            return {"raw": r.text}
    except Exception as e:
        print("❌ 状态请求失败:", e)
        return {}


# =========================
# 触发恢复（核心）
# =========================

def trigger_restore():
    if not RESTORE_URL:
        print("❌ RESTORE_URL 未设置")
        return False

    for i in range(MAX_RETRY):
        try:
            r = requests.get(RESTORE_URL, timeout=10)
            print(f"🚀 restore触发 {i+1}/{MAX_RETRY}: {r.status_code}")
            print(r.text[:200])
            return True
        except Exception as e:
            print("❌ restore失败:", e)
            time.sleep(3)

    return False


# =========================
# 判断状态（修复核心bug）
# =========================

def is_running(data):
    if not data:
        return False

    text = str(data).lower()

    # 兼容各种返回格式
    return (
        "running" in text or
        "starting" in text or
        "\"status\":\"running\"" in text or
        "\"status\": \"running\"" in text
    )


# =========================
# 主循环（修复120s问题关键）
# =========================

def wait_running():
    start = time.time()

    while True:
        data = get_status()

        print(f"[{datetime.now()}] STATUS => {data}")

        if is_running(data):
            print("✅ 服务已运行")
            return True

        if time.time() - start > TIMEOUT:
            print("⚠️ 超时未 Running")
            return False

        time.sleep(CHECK_INTERVAL)


# =========================
# 截图（可选兼容）
# =========================

def save_log_snapshot():
    os.makedirs("scripts/screenshots", exist_ok=True)

    path = f"scripts/screenshots/restore_{int(time.time())}.txt"
    with open(path, "w") as f:
        f.write("restore timeout snapshot\n")

    return path


# =========================
# 主流程
# =========================

def main():
    print("==== Magma Restore Start ====")

    tg("🚀 Restore 开始执行")

    # 1. 触发 restore
    ok = trigger_restore()
    if not ok:
        tg("❌ restore 触发失败")
        return

    # 2. 等待状态
    success = wait_running()

    # 3. 结果处理
    snap = save_log_snapshot()

    if success:
        tg("🎉 服务已恢复 Running")
        tg_photo(snap, "Running OK")
    else:
        tg("❌ 120s 内未进入 Running")
        tg_photo(snap, "Timeout Failure")

    print("==== DONE ====")


if __name__ == "__main__":
    main()
