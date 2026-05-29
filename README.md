# Discord 多功能 AI 機器人

基於 Discord.py 的多功能 AI 聊天機器人，整合多個大型語言模型與多媒體處理能力，可在 Discord 伺服器中提供對話、圖片分析、圖片搜尋、影片摘要、語音生成等服務。

## 功能

| 功能 | 說明 |
|------|------|
| 多模型對話 | 支援 GPT-4o、Claude 3.5 Sonnet、Gemini 1.5 Pro，可即時切換 |
| 圖片分析 | 上傳圖片後由 GPT-4o / Gemini 進行內容描述與翻譯 |
| 圖片生成 | 以自然語言描述生成圖片（DALL-E 3） |
| 圖片搜尋 | 以圖搜圖，返回來源資訊（SauceNao API） |
| 影片摘要 | 上傳影片後提取重點摘要（Gemini 1.5 Pro） |
| 語音生成 | 文字轉語音，支援中文與日文（GPT-SoVITS） |
| 天氣查詢 | 即時氣象資料（中央氣象署 API） |

## 技術

- Python 3 / discord.py
- OpenAI API（GPT-4o、DALL-E 3）
- Anthropic API（Claude 3.5 Sonnet）
- Google Generative AI（Gemini 1.5 Pro）
- DeepSeek API
- SauceNao API（圖片來源搜尋）
- GPT-SoVITS（語音合成）
- aiohttp（非同步 HTTP）

## 快速開始

```bash
pip install -r requirements.txt
cp .env.example .env   # 填入各服務 API Key
python main.py
```

## 環境變數

| 變數 | 說明 |
|------|------|
| `DISCORD_BOT_TOKEN` | Discord Bot Token |
| `OPENAI_API_KEY` | OpenAI API 金鑰 |
| `ANTHROPIC_API_KEY` | Anthropic API 金鑰 |
| `GOOGLE_API_KEY` | Google AI API 金鑰 |
| `DEEPSEEK_API_KEY` | DeepSeek API 金鑰 |
| `SAUCENAO_API_KEY` | SauceNao API 金鑰 |
| `CWA_API_KEY` | 中央氣象署 API 金鑰 |
