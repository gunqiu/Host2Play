import os
import time
import requests

# ==================== 配置区域（从环境变量读取）====================
USER_EMAIL    = os.environ.get("QUARTEX_EMAIL", "")
USER_PASSWORD = os.environ.get("QUARTEX_PASSWORD", "")
SERVER_ID     = os.environ.get("QUARTEX_SERVER_ID", "5070")
TG_CONFIG     = os.environ.get("TG_CONFIG", "")   # 格式: chat_id bot_token
# ==================================================================

LOGIN_URL = "https://api.quartexnode.com/api/v1/auth/login"
RENEW_URL = f"https://api.quartexnode.com/api/v1/server/{SERVER_ID}/renew"

BASE_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9",
    "origin": "https://quartexnode.com",
    "referrer": "https://quartexnode.com/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/109.0.0.0 Safari/537.36"
    )
}

current_token = None

# ──────────────────────────────────────────────
#  Telegram 通知
# ──────────────────────────────────────────────

def _tg_creds():
    if not TG_CONFIG or " " not in TG_CONFIG:
        return None, None
    chat_id, bot_token = TG_CONFIG.split(" ", 1)
    return chat_id.strip(), bot_token.strip()

def _line(char="─", n=28):
    return char * n

def send_telegram(title: str, lines: list[tuple], status: str = "info"):
    """
    status: success | error | warning | info
    lines : [(label, value), ...]  空 label 直接显示 value
    """
    icons = {"success": "✅", "error": "❌", "warning": "⚠️", "info": "💬"}
    icon  = icons.get(status, "💬")

    chat_id, bot_token = _tg_creds()
    if not chat_id:
        return

    body_rows = []
    for label, value in lines:
        if label:
            body_rows.append(f"<b>{label}</b>：{value}")
        else:
            body_rows.append(value)

    msg = (
        f"{icon}  <b>QuartexNode</b>\n"
        f"<code>{_line()}</code>\n"
        f"<b>{title}</b>\n"
        f"<code>{_line()}</code>\n"
        + "\n".join(body_rows)
    )

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
        if resp.status_code != 200:
            print(f"[TG] 发送失败 {resp.status_code}: {resp.text}")
    except requests.exceptions.RequestException as e:
        print(f"[TG] 网络异常: {e}")

# ──────────────────────────────────────────────
#  登录
# ──────────────────────────────────────────────

def login() -> bool:
    global current_token
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] 正在登录...")

    try:
        resp = requests.post(
            LOGIN_URL,
            json={"email": USER_EMAIL, "password": USER_PASSWORD},
            headers=BASE_HEADERS,
            timeout=10
        )
        if resp.status_code in (200, 201):
            token = resp.json().get("access_token")
            if token:
                current_token = f"Bearer {token}"
                print("登录成功，Token 已刷新。")
                return True
            send_telegram("登录响应异常", [
                ("服务器 ID", f"<code>{SERVER_ID}</code>"),
                ("问题", "响应中未找到 access_token"),
                ("时间", ts),
            ], "warning")
        else:
            send_telegram("登录失败", [
                ("服务器 ID", f"<code>{SERVER_ID}</code>"),
                ("状态码", str(resp.status_code)),
                ("响应", resp.text[:200]),
                ("时间", ts),
            ], "error")
    except requests.exceptions.RequestException as e:
        send_telegram("登录网络异常", [
            ("服务器 ID", f"<code>{SERVER_ID}</code>"),
            ("错误", str(e)[:200]),
            ("时间", ts),
        ], "error")
    return False

# ──────────────────────────────────────────────
#  续期
# ──────────────────────────────────────────────

def try_renew() -> bool:
    global current_token
    if not current_token and not login():
        return False

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] 发送续期请求...")

    headers = {**BASE_HEADERS, "authorization": current_token}
    try:
        resp = requests.post(RENEW_URL, headers=headers, timeout=10)
        print(f"状态码: {resp.status_code}")

        try:
            srv_msg = resp.json().get("message", "")
        except Exception:
            srv_msg = resp.text
        print(f"服务器提示: {srv_msg}")

        if resp.status_code == 200:
            print("续期成功！")
            send_telegram("续期成功 🎉", [
                ("服务器 ID", f"<code>{SERVER_ID}</code>"),
                ("账号",      USER_EMAIL),
                ("时间",      ts),
            ], "success")
            return True

        elif resp.status_code == 400:
            print("距到期仍超 24 小时，无需续期。")
            send_telegram("暂无需续期", [
                ("服务器 ID", f"<code>{SERVER_ID}</code>"),
                ("状态",      srv_msg or "距到期仍超 24 小时"),
                ("时间",      ts),
            ], "info")
            return False

        elif resp.status_code in (401, 403):
            print("Token 失效，下次循环将重新登录。")
            current_token = None
            send_telegram("Token 已失效", [
                ("服务器 ID", f"<code>{SERVER_ID}</code>"),
                ("时间",      ts),
                ("",          "将在下次执行时自动重新登录"),
            ], "warning")
            return False

        else:
            send_telegram("续期遇到未知错误", [
                ("服务器 ID", f"<code>{SERVER_ID}</code>"),
                ("状态码",    str(resp.status_code)),
                ("响应",      srv_msg[:200]),
                ("时间",      ts),
            ], "error")
            return False

    except requests.exceptions.RequestException as e:
        send_telegram("续期网络异常", [
            ("服务器 ID", f"<code>{SERVER_ID}</code>"),
            ("错误",      str(e)[:200]),
            ("时间",      time.strftime("%Y-%m-%d %H:%M:%S")),
        ], "error")
        return False

# ──────────────────────────────────────────────
#  入口
# ──────────────────────────────────────────────

def main():
    print("QuartexNode 自动续期脚本启动...")
    send_telegram("脚本已启动", [
        ("服务器 ID", f"<code>{SERVER_ID}</code>"),
        ("账号",      USER_EMAIL),
        ("运行模式",  "每小时检查一次"),
        ("时间",      time.strftime("%Y-%m-%d %H:%M:%S")),
    ], "info")

    login()
    while True:
        try_renew()
        print("─" * 48)
        time.sleep(3600)

if __name__ == "__main__":
    main()
