# Grok (x.ai) 注册机使用教程

## 环境准备

1. 创建并激活虚拟环境（Python 3.10+）：

```bash
cd grok-register
python3 -m venv venv
source venv/bin/activate    # Windows 用 venv\Scripts\activate
```

2. 安装依赖：

```bash
pip install curl_cffi beautifulsoup4 requests python-dotenv
```

3. 准备输出目录：

```bash
mkdir -p keys
```

4. 配置 `.env`（必需）：

```bash
# YesCaptcha（必需，用于绕过 Turnstile 人机验证）
# 注册地址：https://yescaptcha.com/i/PVu8Sc
YESCAPTCHA_KEY="你的_yescaptcha_key"

# 邮件服务（默认使用 MoeMail）
MAIL_SERVICE=moemail
MAIL_SERVICE_KEY="你的_moemail_api_key"
```

## 运行

```bash
cd grok-register
source venv/bin/activate
source .env
export THREADS=1    # 并发数，建议先从 1 开始
python grok.py
```

或一行命令：

```bash
source .env && MAIL_SERVICE=moemail MAIL_SERVICE_KEY=你的key THREADS=1 python grok.py
```

## 邮件服务说明

| 环境变量 | 值 | 说明 |
|---------|-----|------|
| `MAIL_SERVICE` | `moemail`（默认）或 `mailtm` | 选择邮件服务商 |
| `MAIL_SERVICE_KEY` | 你的 API Key | MoeMail 或 Mail.tm 的 API Key |
| `THREADS` | 数字（默认 8） | 并发注册线程数，建议内存在 4GB 以上的服务器设 3~8 |

### MoeMail（推荐）

- 注册地址：https://mail.832818.xyz
- API Key 在后台获取
- 支持临时邮箱自动创建和接收

### Mail.tm（备选）

- 注册地址：https://mail.tm
- 免费账号可用

## 输出文件

- `keys/grok.txt` — 注册成功后的 SSO Token（有效期约 30 天）
- `keys/accounts.txt` — 账号邮箱和密码

## 常见问题

**提示"验证码无效"**
- 确保使用 MoeMail 且 API Key 有效
- 检查 `YESCAPTCHA_KEY` 是否正确配置
- 尝试降低 `THREADS` 到 1

**进程启动后立即退出**
- 检查 `.env` 文件是否创建且包含所有必需变量
- 确认虚拟环境已激活（`source venv/bin/activate`）
