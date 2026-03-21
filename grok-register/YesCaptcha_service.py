import os, re, time, random, requests
from dotenv import load_dotenv
load_dotenv()

class TurnstileService:

    def __init__(self):
        self.yescaptcha_key = os.getenv('YESCAPTCHA_KEY', '').strip()
        self.yescaptcha_api = "https://api.yescaptcha.com"
        self.proxy_list = []
        for v in os.getenv("PROXY_LIST", "").strip().split(","):
            v = v.strip()
            if v:
                self.proxy_list.append(v)
        if not self.proxy_list:
            for v in [os.getenv("HTTP_PROXY"), os.getenv("SOCKS_PROXY")]:
                v = (v or "").strip()
                if v:
                    self.proxy_list.append(v)
                    break

    def _parse_proxy(self, proxy_url):
        if not proxy_url:
            return {}
        m = re.match(r'socks5://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)', proxy_url)
        if m:
            cfg = {"proxyType": "socks5", "proxyAddress": m.group(3), "proxyPort": int(m.group(4))}
            if m.group(1) and m.group(2):
                cfg["proxyLogin"] = m.group(1); cfg["proxyPassword"] = m.group(2)
            return cfg
        m = re.match(r'http://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)', proxy_url)
        if m:
            cfg = {"proxyType": "http", "proxyAddress": m.group(3), "proxyPort": int(m.group(4))}
            if m.group(1) and m.group(2):
                cfg["proxyLogin"] = m.group(1); cfg["proxyPassword"] = m.group(2)
            return cfg
        return {}

    def create_task(self, siteurl, sitekey):
        if not self.yescaptcha_key:
            raise Exception("缺少 YESCAPTCHA_KEY，无法创建任务")
        url = f"{self.yescaptcha_api}/createTask"
        proxy_url = random.choice(self.proxy_list) if self.proxy_list else ""
        proxy_config = self._parse_proxy(proxy_url)
        task = {"type": "TurnstileTask", "websiteURL": siteurl, "websiteKey": sitekey}
        task.update(proxy_config)
        payload = {"clientKey": self.yescaptcha_key, "task": task}
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get('errorId') != 0:
            raise Exception(f"YesCaptcha创建任务失败: {data.get('errorDescription')}")
        return data['taskId']

    def get_response(self, task_id, max_retries=30, initial_delay=5, retry_delay=2):
        if not self.yescaptcha_key:
            raise Exception("缺少 YESCAPTCHA_KEY，无法获取结果")
        url = f"{self.yescaptcha_api}/getTaskResult"
        time.sleep(initial_delay)
        for _ in range(max_retries):
            payload = {"clientKey": self.yescaptcha_key, "taskId": task_id}
            response = requests.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            if data.get('status') == 'ready':
                sol = data.get('solution') or {}
                token = sol.get('gRecaptchaResponse') or sol.get('token') or sol.get('text')
                if not token:
                    print(f"[YesCaptcha] ready但无token, solution keys={list(sol.keys())}")
                    raise Exception("YesCaptcha返回无token字段")
                return token
            time.sleep(retry_delay)
        raise Exception("YesCaptcha 任务超时")

    def solve(self, siteurl, sitekey):
        task_id = self.create_task(siteurl, sitekey)
        return self.get_response(task_id)
