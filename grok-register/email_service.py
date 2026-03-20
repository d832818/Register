"""
email_service.py - Grok 注册机邮箱服务
支持 Mail.tm 和 MoeMail，通过 MAIL_SERVICE 环境变量切换
  MAIL_SERVICE=moemail   → MoeMail (默认)
  MAIL_SERVICE=mailtm    → Mail.tm
"""
import os, time, secrets, re
from typing import Optional, Tuple
import requests

MOE_BASE = "https://mail.832818.xyz"

def _moe_headers(api_key: str) -> dict:
    return {"X-API-Key": api_key, "Content-Type": "application/json"}

def _moe_create(api_key: str) -> Tuple[Optional[str], Optional[str]]:
    name = f"oc{secrets.token_hex(8)}"
    for attempt in range(3):
        try:
            r = requests.post(
                f"{MOE_BASE}/api/emails/generate",
                headers=_moe_headers(api_key),
                json={"name": name, "expiryTime": 86400000, "domain": "832818.xyz"},
                timeout=20
            )
            if r.status_code == 200:
                data = r.json()
                email_addr = data.get("email") or f"{name}@832818.xyz"
                print(f"[MoeMail] 创建: {email_addr}")
                return data.get("id"), email_addr
            else:
                print(f"[MoeMail] 创建失败({r.status_code}): {r.text[:80]}")
        except Exception as e:
            print(f"[MoeMail] 创建异常: {e}")
        time.sleep(2)
    return None, None

def _moe_get_messages(email_id: str, api_key: str) -> list:
    try:
        r = requests.get(
            f"{MOE_BASE}/api/emails/{email_id}",
            headers=_moe_headers(api_key),
            timeout=15
        )
        if r.status_code == 200:
            return r.json().get("messages", [])
    except Exception as e:
        print(f"[MoeMail] 获取消息列表异常: {e}")
    return []

def _moe_get_message(email_id: str, msg_id: str, api_key: str) -> Optional[dict]:
    # 尝试多种 header 和 endpoint
    headers_options = [
        _moe_headers(api_key),
        {**_moe_headers(api_key), "Accept": "application/json, text/html"},
        {**_moe_headers(api_key), "Accept": "application/json"},
    ]
    for extra_headers in headers_options:
        for endpoint in [
            f"{MOE_BASE}/api/emails/{email_id}/{msg_id}",
            f"{MOE_BASE}/api/emails/{email_id}/messages/{msg_id}",
        ]:
            try:
                r = requests.get(endpoint, headers=extra_headers, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    content = data.get("content") or data.get("text") or data.get("html") or data.get("body") or data.get("data", {}).get("content") or ""
                    subject = data.get("subject") or ""
                    if content or subject:
                        print(f"[MoeMail] 获取邮件成功: subject=[{subject}]")
                        return {"subject": subject, "content": content, "html": content, "text": content}
                    print(f"[MoeMail] 邮件内容为空, keys: {list(data.keys())}")
                elif r.status_code == 404:
                    pass  # 试下一个 endpoint
                else:
                    print(f"[MoeMail] 获取邮件失败({r.status_code}): {r.text[:80]}")
            except Exception as e:
                print(f"[MoeMail] 获取邮件异常: {e}")
    # 尝试分享链接获取内容
    try:
        sr = requests.post(
            f"{MOE_BASE}/api/emails/{email_id}/{msg_id}/share",
            headers=_moe_headers(api_key),
            json={"expiresIn": 0},
            timeout=15
        )
        if sr.status_code == 200:
            share_data = sr.json()
            share_url = share_data.get("url") or share_data.get("shareUrl") or share_data.get("link")
            if share_url:
                # 访问分享链接获取内容
                try:
                    gr = requests.get(share_url, timeout=15)
                    if gr.status_code == 200:
                        text = gr.text
                        code_match = re.search(r'\b([A-Z0-9]{4,8})\b', text)
                        if code_match:
                            print(f"[MoeMail] 分享链接提取验证码: {code_match.group(1)}")
                            return {"subject": "分享邮件", "content": text, "html": text, "text": text}
                except:
                    pass
    except:
        pass
    print(f"[MoeMail] 无法获取邮件内容")
    return None

def _moe_poll(email_id: str, api_key: str, timeout: int = 120, interval: float = 5.0) -> Optional[str]:
    """轮询直到收到邮件，返回邮件全文"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        messages = _moe_get_messages(email_id, api_key)
        if messages:
            m = messages[0]
            msg_id = m.get("id")
            if msg_id:
                detail = _moe_get_message(email_id, msg_id, api_key)
                if detail:
                    # 尝试所有可能的内容字段
                    content = detail.get("content") or detail.get("text") or detail.get("html") or ""
                    subject = detail.get("subject") or ""
                    if not content and not subject:
                        # content为null时，尝试从raw响应中提取
                        raw_text = str(detail)
                        print(f"[MoeMail] content=null, raw keys: {list(detail.keys())}")
                    print(f"[MoeMail] 收到邮件: subject=[{subject}]")
                    if content:
                        print(f"[MoeMail] 内容预览: {content[:200]}")
                    return f"{subject} {content}"
        time.sleep(interval)
    print(f"[MoeMail] 轮询超时({timeout}s)，无邮件")
    return None


# ============ Mail.tm ============
MAILTM_BASE = "https://api.mail.tm"

def _mailtm_create() -> Tuple[Optional[str], Optional[str]]:
    from curl_cffi import requests as curl_requests
    timeout = 15
    try:
        domains_r = curl_requests.get(f"{MAILTM_BASE}/domains", timeout=timeout, impersonate="chrome120")
        domains = [d["domain"] for d in domains_r.json().get("hydra:member", []) if d.get("domain")]
    except Exception as e:
        print(f"[Mail.tm] 获取域名失败: {e}")
        return None, None
    if not domains:
        print("[Mail.tm] 无可用域名")
        return None, None
    domain = domains[0]
    local = f"oc{secrets.token_hex(5)}"
    password = secrets.token_urlsafe(18)
    email = f"{local}@{domain}"
    try:
        r1 = curl_requests.post(f"{MAILTM_BASE}/accounts",
                                json={"address": email, "password": password}, timeout=timeout, impersonate="chrome120")
        if r1.status_code != 201:
            print(f"[Mail.tm] 创建失败({r1.status_code}): {r1.text[:80]}")
            return None, None
    except Exception as e:
        print(f"[Mail.tm] 创建异常: {e}")
        return None, None
    try:
        r2 = curl_requests.post(f"{MAILTM_BASE}/token",
                                json={"address": email, "password": password}, timeout=timeout, impersonate="chrome120")
        if r2.status_code == 200:
            token = str(r2.json().get("token", "")).strip()
            if token:
                print(f"[Mail.tm] 账号就绪: {email}")
                return token, email
        else:
            print(f"[Mail.tm] Token失败({r2.status_code})")
    except Exception as e:
        print(f"[Mail.tm] Token异常: {e}")
    return None, None

def _mailtm_poll(token: str, timeout: int = 120, interval: float = 5.0) -> Optional[str]:
    from curl_cffi import requests as curl_requests
    deadline = time.time() + timeout
    req_timeout = 15
    while time.time() < deadline:
        try:
            r = curl_requests.get(f"{MAILTM_BASE}/messages",
                                  headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                                  timeout=req_timeout, impersonate="chrome120")
            if r.status_code == 200:
                msgs = r.json().get("hydra:member", [])
                if msgs:
                    mid = msgs[0]["id"]
                    d = curl_requests.get(f"{MAILTM_BASE}/messages/{mid}",
                                        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                                        timeout=req_timeout, impersonate="chrome120").json()
                    print(f"[Mail.tm] 收到邮件: subject=[{d.get('subject','')}]")
                    return (d.get("subject","") + " " + d.get("text","") + " " + d.get("html",""))
            elif r.status_code == 401:
                print("[Mail.tm] Token失效")
                return None
        except Exception as e:
            print(f"[Mail.tm] 轮询异常: {e}")
        time.sleep(interval)
    print(f"[Mail.tm] 超时({timeout}s)，无邮件")
    return None


# ============ 统一接口 ============
class EmailService:
    def __init__(self, proxies: dict = None, api_key: str = ""):
        self.proxies = proxies
        self.service = os.getenv("MAIL_SERVICE", "moemail").lower()
        self.api_key = api_key or os.getenv("MAIL_SERVICE_KEY", "")

    def create_email(self) -> Tuple[Optional[str], Optional[str]]:
        if self.service == "moemail":
            if not self.api_key:
                return None, None
            return _moe_create(self.api_key)
        else:
            return _mailtm_create()

    def fetch_first_email(self, account_key: str) -> Optional[str]:
        if self.service == "moemail":
            return _moe_poll(account_key, self.api_key)
        else:
            return _mailtm_poll(account_key)
