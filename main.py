import os
import io
import re
import time
import base64
import random
import openai
import asyncio
import aiohttp
import discord
import pathlib
import requests
import textwrap
import tempfile
import datetime
import mimetypes
import anthropic
import threading
import subprocess
from PIL import Image
from io import BytesIO
from google import genai
from typing import Optional, Tuple
from google.genai import types
from dotenv import load_dotenv
from flask import Flask, request
import openai as openai_official  # 如果後續想存取官方 openai 庫的方法
from urllib.parse import urlparse
from discord.ext import commands, tasks
# 注意：以下三個 import / as 的寫法，主要是避免名稱衝突
from openai import APITimeoutError, BadRequestError, OpenAI  # 若有需要 BadRequestError
from openai import OpenAI as DeepSeekOpenAI
from discord import Intents, Embed, app_commands
from google.genai.types import Tool, GoogleSearch
from openai import APIError, APIConnectionError, OpenAIError
try:
    from pydub import AudioSegment
    _PYDUB = True
except ImportError:  # 若無 pydub，可用 subprocess ffmpeg
    _PYDUB = False

# Load .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
SAUCENAO_API_KEY = os.getenv('SAUCENAO_API_KEY')
CWA_API_KEY = os.getenv('CWA_API_KEY')

if not TOKEN:
    print(".env沒找到Discord token")
if not OPENAI_API_KEY:
    print(".env沒找到OpenAI API key")
if not GOOGLE_API_KEY:
    print(".env沒找到GOOGLE API key")      
if not ANTHROPIC_API_KEY:
    print(".env沒找到ANTHROPIC_API_KEY")    
if not DEEPSEEK_API_KEY:
    print(".env沒找到DEEPSEEK_API_KEY")      
if not SAUCENAO_API_KEY:
    print(".env沒找到SauceNAO API key")
if not CWA_API_KEY:
    print(".env沒找到中央氣象署 API key")

#---------------------------------------------------------------------------------------------------------------------
# 初始化設定
openai_official.api_key = OPENAI_API_KEY
genai.Client(api_key=GOOGLE_API_KEY)
async_anthropic_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
deepseek_client = DeepSeekOpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

intents = Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

current_model = "GPT-5.1"
current_image_model = "GPT-5.1"
print(f"以此聊天模型初始化：{current_model}")
print(f"以此讀圖模型初始化：{current_image_model}")

# 不同系模型各自的對話紀錄列表
gpt_conversation_history = []
gemini_conversation_history = []
claude_conversation_history = []
deepseek_chat_conversation_history = []
deepseek_reasoner_conversation_history = []
deepseek_reasoner_fierce_conversation_history = []

_DEFAULT_SYSTEM_PROMPT = "進行至少3000字架構層次完善的長篇深入分析，並且深度、關聯性嚴謹度皆不能落下，然後以繁體中文回答"

gpt_system_message = {"role": "system", "content": _DEFAULT_SYSTEM_PROMPT}
gemini_system_message = _DEFAULT_SYSTEM_PROMPT
claude_system_message = {"role": "system", "content": _DEFAULT_SYSTEM_PROMPT}
deepseek_chat_system_message = {"role": "system", "content": _DEFAULT_SYSTEM_PROMPT}
deepseek_reasoner_system_message = {"role": "system", "content": _DEFAULT_SYSTEM_PROMPT}
deepseek_reasoner_fierce_system_message = {"role": "system", "content": "用贴吧老哥毫不留情、攻击性拉满的口吻，以尖酸刻薄，带有网路用语的方式進行灵活又长篇大论的极端嘲讽和贬低"}

# 發每日通知的頻道ID（設定於 .env）
channel_id = int(os.getenv('DISCORD_CHANNEL_ID', '0'))
channel_id2 = int(os.getenv('DISCORD_CHANNEL_ID2', '0'))

# 監控刪除的機器人ID
SAUCYBOT_ID = 647368715742216193

#---------------------------------------------------------------------------------------------------------------------
# 地牛地震通知
# 先把縮圖連結定義好
# 2025/02/16 中央氣象屬禁止地牛傳遞地震資訊，因此此功能已失效
EARTHQUAKE_IMG_URL = os.getenv("EARTHQUAKE_IMG_URL", "")

app = Flask(__name__)
@app.route('/earthquake', methods=['POST'])
def earthquake_alert():
    try:
        # 從 POST 請求中獲取地震資訊
        seismic_intensity = request.form.get('magnitude')  # 地牛傳遞的「所在地震度」
        seconds_to_arrival = request.form.get('seconds_to_arrival')  # 傳遞的「震波抵達秒數」

        if not seismic_intensity or not seconds_to_arrival:
            print("缺少必要參數")
            return "缺少必要參數", 400

        # 確保秒數為整數格式
        try:
            seconds_to_arrival = int(seconds_to_arrival)
        except ValueError:
            print("無效秒數格式")
            return "無效秒數格式", 400

        # 轉換震度格式
        def format_seismic_intensity(intensity):
            intensity = intensity.split('.')[0]  # 去除可能的小數點
            intensity_mapping = {
                '1': '1級',
                '2': '2級',
                '3': '3級',
                '4': '4級',
                '5-': '5弱級',
                '5+': '5強級',
                '6-': '6弱級',
                '6+': '6強級',
                '7': '7級'
            }
            return intensity_mapping.get(intensity, f"{intensity}級")

        formatted_intensity = format_seismic_intensity(seismic_intensity)

        # 取得現在時間
        current_time_earthquake = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 建立 Embed
        embed = Embed(
            title="🥺地震🥺",
            description=(
                f"**林口預計震度**：{formatted_intensity}\n"
                f"**震波抵達時間**：{seconds_to_arrival} 秒後\n"
                f"**現在時間**：{current_time_earthquake}"
            ),
            color=0xFCAF17  # 紅色
        )

        # 直接使用遠端圖片連結
        embed.set_thumbnail(url=EARTHQUAKE_IMG_URL)

        # 發送到 Discord 頻道
        channel_main = bot.get_channel(channel_id)
        channel_eq2  = bot.get_channel(channel_id2)

        if channel_main:
            asyncio.run_coroutine_threadsafe(channel_main.send(embed=embed), bot.loop)
        if channel_eq2:
            asyncio.run_coroutine_threadsafe(channel_eq2.send(embed=embed), bot.loop)

        print(f"地震通知：震度 {formatted_intensity}，抵達時間 {seconds_to_arrival} 秒")
        return "通知已發送", 200

    except Exception as e:
        print(f"發生錯誤：{str(e)}")
        return f"通知失敗：{str(e)}", 500

def run_flask():
    app.run(host='0.0.0.0', port=12345)

flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

#---------------------------------------------------------------------------------------------------------------------
# 中央氣象署地震報告
def parse_cwa_list(json_data) -> list[dict]:
    eqs = json_data.get("records", {}).get("Earthquake", [])
    results = []

    for eq in eqs:
        report_content = eq.get("ReportContent", "")
        eq_no = eq.get("EarthquakeNo", "無編號")

        # 移除前綴 e.g. "01/21-01:06"
        import re
        report_content = re.sub(r"^\d{2}/\d{2}-\d{2}:\d{2}", "", report_content).strip()

        eq_info = eq.get("EarthquakeInfo", {})
        origin_time = eq_info.get("OriginTime", "")
        focal_depth = eq_info.get("FocalDepth", 0.0)
        mag_info = eq_info.get("EarthquakeMagnitude", {})
        mag_value = mag_info.get("MagnitudeValue", 0.0)
        epicenter = eq_info.get("Epicenter", {})
        location = epicenter.get("Location", "")

        # 時間格式 -> "YYYY/MM/DD\n上午 HH:MM:SS"
        occur_time_str = origin_time
        try:
            dt = datetime.datetime.strptime(origin_time, "%Y-%m-%d %H:%M:%S")
            am_pm = "上午" if dt.hour < 12 else "下午"
            occur_time_str = dt.strftime(f"%Y/%m/%d\n{am_pm} %H:%M:%S")
        except:
            pass

        focal_depth_str = f"{focal_depth} 公里"

        pattern = r"最大震度([\u4e00-\u9fa5A-Za-z0-9+\-]+)。?"
        match = re.search(pattern, report_content)
        max_intensity_text = match.group(1) if match else "不明"

        report_image_url = eq.get("ReportImageURI", "")

        results.append({
            "desc_text":         report_content,
            "eq_no":             eq_no,
            "occur_time_str":    occur_time_str,
            "epicenter_str":     location,
            "mag_value":         mag_value,
            "focal_depth_str":   focal_depth_str,
            "max_intensity_str": max_intensity_text,
            "report_image_url":  report_image_url
        })

    return results

def build_earthquake_embed(eq_data: dict, title_text: str, show_eq_no: bool) -> Embed:
    desc_text       = eq_data["desc_text"]
    eq_no           = eq_data["eq_no"]
    occur_time_str  = eq_data["occur_time_str"]
    epicenter_str   = eq_data["epicenter_str"]
    mag_value       = eq_data["mag_value"]
    focal_depth_str = eq_data["focal_depth_str"]
    max_intensity   = eq_data["max_intensity_str"]
    report_image_url= eq_data["report_image_url"]

    embed = Embed(title=title_text, description=desc_text, color=0xFCAF17)

    # 是否顯示地震編號
    if show_eq_no:
        embed.add_field(name="編號", value=eq_no, inline=True)

    embed.add_field(name="發生時間", value=occur_time_str, inline=True)
    embed.add_field(name="震央位置", value=epicenter_str, inline=True)

    embed.add_field(name="規模", value=str(mag_value), inline=True)
    embed.add_field(name="深度", value=focal_depth_str, inline=True)
    embed.add_field(name="最大震度", value=max_intensity, inline=True)

    if report_image_url:
        embed.set_image(url=report_image_url)

    return embed

last_earthquake_no = None
first_run = True  # 用於判斷是否首次啟動後的第一次執行

@tasks.loop(seconds=30)
async def auto_check_earthquake():
    global last_earthquake_no, first_run
    if not CWA_API_KEY:
        return

    url_15 = (
        f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0015-001?"
        f"Authorization={CWA_API_KEY}&limit=1&format=JSON"
    )
    try:
        r = requests.get(url_15, headers={"Accept": "application/json"}, timeout=10)
        data = r.json()

        eq_list = parse_cwa_list(data)  # 回傳一個 list
        if not eq_list:
            return  # 無地震資料
        
        # 既然 limit=1，所以 eq_list[0] 就是我們要的那一筆資料
        eq_data = eq_list[0]
        eq_no = eq_data["eq_no"]

        if first_run:
            # 第一次跑，只更新 last_earthquake_no，不發送
            last_earthquake_no = eq_no
            first_run = False
            print(f"首次啟動，已更新 last_earthquake_no = {eq_no}")
        else:
            # 之後才檢查是否有新地震
            if eq_no != last_earthquake_no:
                channel_main = bot.get_channel(channel_id)

                embed = build_earthquake_embed(eq_data, "最新顯著有感地震", True)

                if channel_main:
                    await channel_main.send(embed=embed)

                last_earthquake_no = eq_no

    except Exception as e:
        print("自動抓地震報告失敗:", e)

#---------------------------------------------------------------------------------------------------------------------
# ========== 新版 API (GPT-5) 使用的 blocking 函式 (最終修正版) ==========
def _blocking_gpt51_response(model: str, user_input: str, max_output_tokens: int, reasoning: dict = None, text_params: dict = None):
    """
    專為 client.responses.create 設計，並包含健壯的回應解析邏輯。
    """
    client = openai.Client(api_key=OPENAI_API_KEY)
    params = {
        "model": model,
        "input": user_input,
        "max_output_tokens": max_output_tokens
    }
    if reasoning:
        params["reasoning"] = reasoning
    if text_params:
        params["text"] = text_params
    
    response = client.responses.create(**params)
    
    output_text = ""
    # 檢查 'output' 屬性是否存在且不為 None
    if hasattr(response, "output") and response.output:
        for item in response.output:
            # 關鍵修正：在遍歷前，檢查 item.content 是否存在且不為 None
            if hasattr(item, "content") and item.content:
                for content in item.content:
                    # 同時也檢查 content 本身和它的 text 屬性
                    if hasattr(content, "text") and content.text is not None:
                        output_text += content.text
    
    # 如果迴圈結束後 output_text 仍然是空的，可以回傳一個提示訊息
    return output_text if output_text else "（模型未回傳任何內容，可能已被過濾或為空回應）"

# --- GPT-5 高層 Async 函式 (修改後) ---
async def GPT51_response(user_text: str, enhance: bool, reasoning_effort: str = "medium", verbosity: str = "medium") -> str:
    global gpt_conversation_history # <--- 使用 gpt5 的歷史
    # 1. 將當前使用者的話加入 gpt5 的歷史
    gpt_conversation_history.append({"role": "user", "content": user_text})
    
    conversation_parts = []
    if enhance:
        conversation_parts.append(gpt_system_message['content'])

    # 4. 關鍵步驟：遍歷 gpt5 的歷史
    for message in gpt_conversation_history[-50:]:
        role = message["role"]
        content = message["content"]
        if role == "user":
            conversation_parts.append(f"User: {content}")
        elif role == "assistant":
            conversation_parts.append(f"Assistant: {content}")
            
    final_input = "\n\n".join(conversation_parts)

    reasoning_param = {"effort": reasoning_effort} if reasoning_effort else None
    text_param = {"verbosity": verbosity} if verbosity else None
    
    answer = await asyncio.to_thread(
        _blocking_gpt51_response,
        model="gpt-5.1",
        user_input=final_input,
        max_output_tokens=128000,
        reasoning=reasoning_param,
        text_params=text_param
    )
    
    # 6. 將模型的回答也加入 gpt5 的歷史
    gpt_conversation_history.append({"role": "assistant", "content": answer})
    return answer

# ==========  claude-opus-4-5: 串流 ==========
async def Claude_opus_response(text, enhance=True):
    global claude_conversation_history

    claude_conversation_history.append({"role": "user", "content": text})
    messages_to_send = claude_conversation_history[-20:]

    formatted_messages = []
    for m in messages_to_send:
        formatted_messages.append({
            "role": m["role"],
            "content": [{"type": "text", "text": m["content"]}]
        })

    api_system_parameter = [] # 預設為空列表
    if enhance:
        if claude_system_message and isinstance(claude_system_message.get("content"), str) and claude_system_message["content"].strip():
            # 從 claude_system_message 提取 content 並構建成列表形式
            api_system_parameter = [{"type": "text", "text": claude_system_message["content"]}]
        else:
            # 可選：如果 enhance 為 True 但系統訊息配置不正確，打印警告
            print(f"警告: 'enhance' 為 True，但 claude_system_message 未正確配置或其 content 為空。將使用空列表作為系統提示。claude_system_message: {claude_system_message}")

    response_chunks = []
    answer = ""
    try:
        async with async_anthropic_client.messages.stream(
            model="claude-opus-4-5-20251101",
            max_tokens=64000,
            temperature=0.7,
            system=api_system_parameter,
            messages=formatted_messages
        ) as stream:
            async for text_chunk in stream.text_stream:
                response_chunks.append(text_chunk)
        
        answer = "".join(response_chunks)

    except anthropic.APIError as e:
        # 確保錯誤信息能夠清晰地傳遞出去
        error_message = f"Claude API 錯誤: {e}"
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            try:
                # 嘗試解析 JSON 錯誤詳情
                error_details = e.response.json()
                error_message += f" | 詳情: {error_details}"
            except: # noqa
                error_message += f" | 原始響應: {e.response.text}"
        print(error_message) # 打印到控制台
        raise # 重新拋出，讓 Discord 命令的 try-except 處理對用戶的顯示

    except Exception as ex:
        print(f"發生未預期錯誤: {ex}")
        raise

    claude_conversation_history.append({"role": "assistant", "content": answer})
    return answer

# ========== DeepSeek Chat (V3) ==========
def _blocking_deepseek_chat(model: str, messages):
    """阻塞式呼叫 DeepSeek Chat"""
    try:
        resp = deepseek_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=8192
        )
        return resp
    except Exception as e:
        print(f"DeepSeek 呼叫失敗: {e}")
        raise

async def deepseek_chat_response(user_text: str, enhance: bool = True) -> str:
    global deepseek_chat_conversation_history

    # 1) 組合 messages
    messages = []
    if enhance:
        messages.append(deepseek_chat_system_message)
    messages.extend(deepseek_chat_conversation_history)
    messages.append({"role": "user", "content": user_text})

    try:
        # 2) 在背景執行緒阻塞呼叫
        response = await asyncio.to_thread(_blocking_deepseek_chat, "deepseek-chat", messages)
        # 3) 取出最終回答
        output_text = response.choices[0].message.content
    except Exception as e:
        # 方便除錯
        print("[DEBUG deepseek_chat_response] 出錯了:", e)
        raise

    # 4) 寫回紀錄
    deepseek_chat_conversation_history.append({"role": "user", "content": user_text})
    deepseek_chat_conversation_history.append({"role": "assistant", "content": output_text})

    return output_text

def _blocking_deepseek_reasoner(model: str, messages):
    try:
        resp = deepseek_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=65536
        )
        return resp

    except APIError as ae:
        print("APIError:", ae, ae.json_body, ae.http_status)
        raise
    except APIConnectionError as ace:
        print("APIConnectionError:", ace)
        raise
    except OpenAIError as oe:
        print("OpenAIError:", oe)
        raise

async def deepseek_reasoner_response(user_text: str, enhance: bool = True, show_reasoning: bool = False) -> str:
    global deepseek_reasoner_conversation_history

    # 1) 組合 messages
    messages = []
    if enhance:
        messages.append(deepseek_reasoner_system_message)
    messages.extend(deepseek_reasoner_conversation_history)
    messages.append({"role": "user", "content": user_text})

    try:
        # 2) 在背景執行緒阻塞呼叫
        response = await asyncio.to_thread(_blocking_deepseek_reasoner, "deepseek-reasoner", messages)
        # 3) 取 reasoning_content & content
        reasoning_content = getattr(response.choices[0].message, "reasoning_content", "")
        final_answer = getattr(response.choices[0].message, "content", "")
    except Exception as e:
        print("[DEBUG deepseek_reasoner_response] 出錯了:", e)
        raise

    # 4) 寫回紀錄 (user, assistant)
    deepseek_reasoner_conversation_history.append({"role": "user", "content": user_text})
    deepseek_reasoner_conversation_history.append({"role": "assistant", "content": final_answer})

    # 5) show_reasoning?
    if show_reasoning and reasoning_content:
        return f"[思維鏈]\n{reasoning_content}\n\n---\n\n[最終回答]\n{final_answer}"
    else:
        return final_answer

def _blocking_deepseek_reasoner_fierce(model: str, messages):
    try:
        resp = deepseek_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=65536
        )
        return resp

    except APIError as ae:
        print("APIError:", ae, ae.json_body, ae.http_status)
        raise
    except APIConnectionError as ace:
        print("APIConnectionError:", ace)
        raise
    except OpenAIError as oe:
        print("OpenAIError:", oe)
        raise

async def deepseek_reasoner_fierce_response(user_text: str, enhance: bool = True, show_fierce_reasoning: bool = False) -> str:
    global deepseek_reasoner_fierce_conversation_history

    # 1) 組合 messages
    messages = []
    if enhance:
        messages.append(deepseek_reasoner_fierce_system_message)
    messages.extend(deepseek_reasoner_fierce_conversation_history)
    messages.append({"role": "user", "content": user_text})

    try:
        # 2) 在背景執行緒阻塞呼叫
        response = await asyncio.to_thread(_blocking_deepseek_reasoner_fierce, "deepseek-reasoner", messages)
        # 3) 取 reasoning_content & content
        fierce_reasoning_content = getattr(response.choices[0].message, "reasoning_content", "")
        final_answer = getattr(response.choices[0].message, "content", "")
    except Exception as e:
        print("[DEBUG deepseek_reasoner_response] 出錯了:", e)
        raise

    # 4) 寫回紀錄 (user, assistant)
    deepseek_reasoner_fierce_conversation_history.append({"role": "user", "content": user_text})
    deepseek_reasoner_fierce_conversation_history.append({"role": "assistant", "content": final_answer})

    # 5) show_reasoning?
    if show_fierce_reasoning and fierce_reasoning_content:
        return f"**[DeepSeek R1嘴砲思維鏈]**\n{fierce_reasoning_content}\n\n---\n\n**[DeepSeek R1嘴砲內容]**\n{final_answer}"
    else:
        return final_answer  

# Google 搜尋工具物件
google_search_tool = Tool(google_search=GoogleSearch())

# Gemini系多輪對話
def build_prompt(history: list) -> str:
    """
    將 history (列表) 中的訊息逐條拼接成一個最終的大字串，
    用來當作 generate_content 的輸入。
    """
    prompt_segments = []
    for msg in history:
        role = msg["role"]
        content = msg["content"]

        if role == "system":
            prompt_segments.append(f"System: {content}\n")
        elif role == "user":
            prompt_segments.append(f"User: {content}\n")
        elif role == "assistant":
            prompt_segments.append(f"Assistant: {content}\n")
        else:
            prompt_segments.append(f"{role.capitalize()}: {content}\n")

    # 最後加上 "Assistant: " 代表想要模型接著回答
    prompt_segments.append("Assistant: ")
    return "".join(prompt_segments)

# Gemini系模型的回復函式
async def Gemini_response(user_message: str, enhance: bool = True, use_google_search: bool = False) -> str:
    client = genai.Client(api_key=GOOGLE_API_KEY)
    system_instruction = gemini_system_message if enhance else None
    tools = [Tool(google_search=GoogleSearch())] if use_google_search else []

    # A) 把本輪使用者訊息存入多輪對話紀錄
    gemini_conversation_history.append({"role": "user", "content": user_message})

    # B) 建立完整的 prompt
    prompt_text = build_prompt(gemini_conversation_history)

    try:
        # C) 呼叫 generate_content
        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=[prompt_text],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=1,
                top_p=0.95,
                max_output_tokens=65536,
                tools=tools,
                response_modalities=["TEXT"]
            )
        )

        # 解析回覆
        result = ""
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                result += part.text

        final_reply = result.strip()

        # D) 將模型回覆寫回多輪對話紀錄
        gemini_conversation_history.append({"role": "assistant", "content": final_reply})

        return final_reply

    except Exception as e:
        return f"錯誤：{str(e)}"

#---------------------------------------------------------------------------------------------------------------------
# 讀圖模型設定
# gpt5讀圖回復 (最終修正版)
def _blocking_gpt51_image_response(image_url: str, text: str, reasoning_effort: str, verbosity: str):
    """
    使用您驗證過可行的 chat.completions.create API，並動態加入新參數。
    """
    client = openai.Client(api_key=OPENAI_API_KEY)

    # 您的 messages 結構是完全正確的
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
                        "detail": "high"
                    },
                },
            ],
        }
    ]

    # 建立一個參數字典，只包含確定會傳送的參數
    params = {
        "model": "gpt-5.1", # 使用您確認過可用的模型名稱
        "messages": messages,
        "max_completion_tokens": 128000,
    }

    # 關鍵修正：如果參數存在，就將其作為頂層參數加入字典
    if reasoning_effort:
        params["reasoning_effort"] = reasoning_effort
    
    if verbosity:
        # 根據您的範例，我們推斷 verbosity 也會是頂層參數
        params["verbosity"] = verbosity

    # 使用 **params 將字典解包成關鍵字參數傳入
    response = client.chat.completions.create(**params)
    
    return response.choices[0].message.content

# 對應的 Async 函式
async def GPT51_image_response(image_url: str, text: str, reasoning_effort: str, verbosity: str):
    answer = await asyncio.to_thread(_blocking_gpt51_image_response, image_url, text, reasoning_effort, verbosity)
    return answer

def download_and_encode_image(image_url: str) -> str:
    """
    從遠端 URL 下載圖片並轉成 base64 編碼字串。
    回傳值格式為： 'iVBORw0KGgoAAAANSUhEUgAA...'
    """
    resp = requests.get(image_url)
    resp.raise_for_status()  # 若下載失敗會丟出例外
    b64_data = base64.b64encode(resp.content).decode('utf-8')
    return b64_data

def _blocking_gemini_image_response(image_url: str, text: str) -> str:
    client = genai.Client(api_key=GOOGLE_API_KEY)

    # 1) 從遠端下載圖片
    resp = requests.get(image_url)
    resp.raise_for_status()
    image_bytes = resp.content

    # 2) 依檔名判斷副檔名
    #    (也可以改用別的方法，如果你已確定傳進來的一定是 .png, .jpg, etc.)
    extension = os.path.splitext(image_url)[1].lower()

    if extension in [".jpeg", ".jpg"]:
        mime_type = "image/jpeg"
    elif extension == ".png":
        mime_type = "image/png"
    elif extension == ".gif":
        mime_type = "image/gif"
    elif extension == ".webp":
        mime_type = "image/webp"
    else:
        # 如果遇到不支援或未知格式，可以預設 "image/jpeg"
        # 或改成 "application/octet-stream" 看需求
        mime_type = "image/jpeg"

    # 3) 組出 contents: [文字, 圖片Part]
    prompt_contents = [
        text,
        types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type
        )
    ]

    # 4) 呼叫 generate_content
    try:
        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=prompt_contents,
            config=types.GenerateContentConfig(
                temperature=1,
                top_p=0.95,
                max_output_tokens=65536,
                response_modalities=["TEXT"]
            )
        )
    except Exception as e:
        return f"錯誤：{str(e)}"

    # 5) 解析回覆
    result = []

    # 防止NoneType 錯誤
    if not response or not response.candidates:
        return "Gemini沒給任何回應"

    for part in response.candidates[0].content.parts:
        if hasattr(part, "text") and part.text:
            result.append(part.text)

    return "".join(result).strip() or "沒給任何可用的文字內容"

async def gemini_image_response(image_url: str, text: str) -> str:
    """
    非同步呼叫 Gemini (內部仍是阻塞，但藉由 asyncio.to_thread 包起來)。
    """
    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(
        None,  # 預設執行緒池
        _blocking_gemini_image_response,  # 要呼叫的目標函式
        image_url,
        text
    )
    return answer

#---------------------------------------------------------------------------------------------------------------------
# 切字用
MAX_DISCORD_LEN = 2000

async def send_in_chunks(dest, content: str, prefix: str = "") -> None:
    """
    將 content 依 Discord 長度限制切塊傳送。
    dest 必須具備 .send() coroutine (TextChannel、InteractionFollowup 皆可)
    """
    # 防呆：prefix 自身過長
    if prefix and len(prefix) >= MAX_DISCORD_LEN:
        prefix = prefix[:MAX_DISCORD_LEN - 1] + "…"

    # 一條訊息搞定
    if len(content) <= MAX_DISCORD_LEN - len(prefix):
        await dest.send(prefix + content)
        return

    # 先送 prefix（若有）
    if prefix:
        await dest.send(prefix.rstrip())

    # 固定字元切片，確保不超長且無空訊息
    for i in range(0, len(content), MAX_DISCORD_LEN):
        chunk = content[i:i + MAX_DISCORD_LEN]
        if chunk:
            await dest.send(chunk)

#---------------------------------------------------------------------------------------------------------------------
# 機器人個別指令設定
@bot.tree.command(name="chat", description="花帆")
@app_commands.describe(
    enhance="是否加強提示詞，預設開",
    reasoning_effort="限【GPT-5】推理強度，預設medium",
    verbosity="限【GPT-5】回覆詳細度，預設medium",
    show_reasoning="限【DeepSeek-R1】是否顯示思維鏈，預設關",
    use_google_search="限【Gemini】是否Google搜尋，預設關",
)
@app_commands.choices(reasoning_effort=[
    app_commands.Choice(name="Minimal(適合指令遵循)", value="minimal"),
    app_commands.Choice(name="Low(較少推理)", value="low"),
    app_commands.Choice(name="Medium(預設平衡)", value="medium"),
    app_commands.Choice(name="High(最詳盡多推理)", value="high"),
])
@app_commands.choices(verbosity=[ 
    app_commands.Choice(name="Low(簡潔)", value="low"),
    app_commands.Choice(name="Medium(預設平衡)", value="medium"),
    app_commands.Choice(name="High(詳細)", value="high"),
])
async def chat(
    interaction: discord.Interaction,
    message: str,
    enhance: bool = True,
    reasoning_effort: str = None,
    verbosity: str = None,
    show_reasoning: bool = False,
    use_google_search: bool = False
):
    await interaction.response.defer()

    # --- 防呆與回饋邏輯 ---
    # 準備一個回饋給使用者的前綴訊息
    prefix = f"目前模型: **{current_model}**\n"
    final_reasoning_effort = "medium" # GPT-5 預設值
    final_verbosity = "medium" # GPT-5 預設值

    if current_model == "GPT-5.1":
        if reasoning_effort:
            final_reasoning_effort = reasoning_effort
        if verbosity: # 新增對 verbosity 的處理
            final_verbosity = verbosity
            
        # 在回饋中同時顯示兩個參數的設定
        prefix += f"推理強度: **{final_reasoning_effort}**\n"
        prefix += f"詳細程度: **{final_verbosity}**\n\n"

    else:
        # 如果在非 GPT-5 模型下使用了專用參數，給予提示
        if reasoning_effort:
            prefix += f"*(推理強度僅對GPT-5有效)*\n"
        if verbosity:
            prefix += f"*(詳細程度僅對GPT-5有效)*\n"
        if reasoning_effort or verbosity:
             prefix += "\n"

    try:
        if current_model == "GPT-5.1":
            response = await GPT51_response(message, enhance, final_reasoning_effort, final_verbosity)
        elif current_model == "Gemini-3-Pro":
            response = await Gemini_response(message, enhance, use_google_search)
        elif current_model == "Deepseek-Reasoner":
            response = await deepseek_reasoner_response(message, enhance, show_reasoning)        
        elif current_model == "Claude-4-5-Opus":
            response = await Claude_opus_response(message, enhance)
        elif current_model == "Deepseek-Chat":
            response = await deepseek_chat_response(message, enhance)
        else:
            response = "（未知或尚未支援的模型）"

        await send_in_chunks(interaction.followup, response, prefix=prefix)

    except ValueError as e:
        await interaction.followup.send(f"錯誤：{e}")
    except Exception as ex:
        # 建議印出詳細錯誤以供偵錯
        import traceback
        traceback.print_exc()
        await interaction.followup.send(f"發生未預期的錯誤: `{ex}`")

#---------------------------------------------------------------------------------------------------------------------
# 機器人個別指令設定
@bot.tree.command(name="chat_model", description="切換聊天模型")
@app_commands.choices(choices=[
    app_commands.Choice(name="GPT-5.1", value="GPT-5.1"),
    app_commands.Choice(name="Gemini-3-Pro", value="Gemini-3-Pro"),
    app_commands.Choice(name="DeepSeek Reasoner (R1)", value="Deepseek-Reasoner"),
    app_commands.Choice(name="Claude 4-5 Opus", value="Claude-4-5-Opus"),
    app_commands.Choice(name="DeepSeek Chat (V3)", value="Deepseek-Chat")
])
async def chat_model(interaction: discord.Interaction, choices: app_commands.Choice[str]):
    global current_model
    global deepseek_reasoner_conversation_history

    old_model = current_model
    current_model = choices.value
    print(f"已切換到模型：{choices.name}")

    # 只有當原本不是 R1，而切換到 R1 時，自動重置 R1 記錄
    if old_model != "Deepseek-Reasoner" and current_model == "Deepseek-Reasoner":
        deepseek_reasoner_conversation_history = []
        print("已自動重置 DeepSeek Reasoner 對話紀錄。")

    await interaction.response.send_message(f"已切換到模型：{choices.name}")

#---------------------------------------------------------------------------------------------------------------------
# 機器人個別指令設定
@bot.tree.command(name="嘴", description="用 DeepSeek R1 嘴砲")
@app_commands.describe(
    show_fierce_reasoning="是否顯示 DeepSeek R1 嘴砲思維鏈(True/False)，預設關閉"
)
async def fierce_mode(
    interaction: discord.Interaction,
    message: str,
    show_fierce_reasoning: bool = False
):
    await interaction.response.defer()   # 延長回應時間

    try:
        # 強制 enhance=True
        response = await deepseek_reasoner_fierce_response(
            user_text=message,
            enhance=True,
            show_fierce_reasoning=show_fierce_reasoning
        )

        prefix = "【R1 嘴砲】\n\n"
        await send_in_chunks(interaction.followup, response, prefix=prefix)

    except ValueError as e:
        await interaction.followup.send(f"錯誤：{e}")
    except Exception as ex:
        await interaction.followup.send(f"發生錯誤：{ex}")

#---------------------------------------------------------------------------------------------------------------------
# 機器人個別指令設定
gpt51_image_reasoning_effort = "low"
gpt51_image_verbosity = "low"

@bot.tree.command(name="image_model", description="設定讀圖模型參數")
@app_commands.describe(
    model="要切的讀圖模型",
    reasoning_effort="【僅GPT-5】設定推理強度",
    verbosity="【僅GPT-5】設定詳細程度"
)
@app_commands.choices(model=[
     app_commands.Choice(name="GPT-5.1", value="GPT-5.1"),
     app_commands.Choice(name="Gemini-3-Pro", value="Gemini-3-Pro")
])
@app_commands.choices(reasoning_effort=[
    app_commands.Choice(name="Minimal(適合指令遵循)", value="minimal"),
    app_commands.Choice(name="Low(較少推理)", value="low"),
    app_commands.Choice(name="Medium(預設平衡)", value="medium"),
    app_commands.Choice(name="High(最詳盡多推理)", value="high"),
])
@app_commands.choices(verbosity=[ 
    app_commands.Choice(name="Low(簡潔)", value="low"),
    app_commands.Choice(name="Medium(預設平衡)", value="medium"),
    app_commands.Choice(name="High(詳細)", value="high"),
])
async def image_model(interaction: discord.Interaction, model: app_commands.Choice[str], reasoning_effort: str = None, verbosity: str = None):
    global current_image_model, gpt51_image_reasoning_effort, gpt51_image_verbosity

    # 1. 切換模型
    current_image_model = model.value
    response_text = f"已切換到讀圖模型：**{model.name}**\n"
    print(f"已切換到讀圖模型：{model.name}") 

    # 2. 如果選擇了 GPT-5，就儲存相關設定
    if current_image_model == "GPT-5.1":
        if reasoning_effort:
            gpt51_image_reasoning_effort = reasoning_effort
        if verbosity:
            gpt51_image_verbosity = verbosity
        
        # 在回饋訊息中告知使用者目前的設定
        response_text += f"推理強度設為: **{gpt51_image_reasoning_effort}**\n"
        response_text += f"詳細程度設為: **{gpt51_image_verbosity}**"

    # 3. 如果選了別的模型但又設定了 GPT-5 參數，給予提示
    elif reasoning_effort or verbosity:
        response_text += "\n*(推理強度與詳細程度參數僅在選擇GPT-5時生效)*"
        
    await interaction.response.send_message(response_text)

#---------------------------------------------------------------------------------------------------------------------
# 機器人個別指令設定
@bot.tree.command(name="reset", description="重製對話上下文")
async def clear_all(interaction: discord.Interaction):
    global gpt_conversation_history
    global gemini_conversation_history
    global claude_conversation_history
    global deepseek_chat_conversation_history
    global deepseek_reasoner_conversation_history
    global deepseek_reasoner_fierce_conversation_history

    gpt_conversation_history = []
    gemini_conversation_history = []
    claude_conversation_history = []
    deepseek_chat_conversation_history = []
    deepseek_reasoner_conversation_history = []
    deepseek_reasoner_fierce_conversation_history = []
    await interaction.response.send_message("上下文已重製")

#---------------------------------------------------------------------------------------------------------------------
# 機器人個別指令設定
# hdcu
#---------------------------------------------------------------------------------------------------------------------
# 機器人個別指令設定
@bot.tree.command(name="forward", description="轉傳")
async def forward(interaction: discord.Interaction, *, message: str):
    # 確認交互，這非常重要！
    await interaction.response.defer(ephemeral=True)

    target_channel = interaction.channel

    # 正則表達式查找URLs
    url_regex = r'(https?://[^\s]+)'
    urls = re.findall(url_regex, message)

    # 提取消息中的文本內容（不包括URL）
    text_content = re.sub(url_regex, '', message).strip()

    if urls:
        # 遍歷所有找到的URLs
        for url in urls:
            # 檢查URL是否是圖片鏈接
            if url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                # 如果是圖片鏈接，創建嵌入內容
                embed = Embed()
                embed.set_image(url=url)  # 設置圖片
                await target_channel.send(embed=embed)  # 發送嵌入內容
            else:
                # 如果是普通的網頁鏈接（如文章），直接發送鏈接
                await target_channel.send(content=url)

        # 發送文本內容（如果有的話）
        if text_content:
            await target_channel.send(content=text_content)
    else:
        # 如果沒有URL，只發送文本內容
        await target_channel.send(content=message)

    # 給用户發送一個私有響應
    await interaction.followup.send(content="好ㄌ", ephemeral=True)

#---------------------------------------------------------------------------------------------------------------------
# 機器人個別指令設定
@bot.tree.command(name="earthquake", description="查詢最新地震報告")
@app_commands.describe(report_type="查哪種地震報告", count="查最新幾筆(1~10)")
@app_commands.choices(report_type=[
    app_commands.Choice(name="顯著有感地震", value="E-A0015-001"),
    app_commands.Choice(name="小區域有感地震", value="E-A0016-001"),
])
async def earthquake_command(
    interaction: discord.Interaction,
    report_type: app_commands.Choice[str],
    count: int
):

    if not CWA_API_KEY:
        await interaction.response.send_message("中央氣象署 API Key失效", ephemeral=True)
        return

    # 限制 count 在 1~10
    if count < 1 or count > 10:
        await interaction.response.send_message("筆數:1~10", ephemeral=True)
        return

    dataset_id = report_type.value
    # 判斷顯示標題 & 是否顯示編號
    if dataset_id == "E-A0015-001":
        embed_title = "最新顯著有感地震"
        show_eq_no = True
    else:
        embed_title = "最新小區域有感地震"
        show_eq_no = False

    # URL 加上 ?limit={count}
    url = (
        f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{dataset_id}?"
        f"Authorization={CWA_API_KEY}&limit={count}&format=JSON"
    )

    try:
        r = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
        data = r.json()

        # 解析多筆
        eq_list = parse_cwa_list(data)
        if not eq_list:
            await interaction.response.send_message("目前無相關報告", ephemeral=True)
            return

        # 逐一把 eq_list 裡的資料轉成 Embed
        embeds = []
        for i, eq_data in enumerate(eq_list, start=1):
            # 可以在標題後面加 "(i/N)" 表示第幾筆
            title_this = f"{embed_title} (第{i}筆)"
            embed = build_earthquake_embed(eq_data, title_this, show_eq_no)
            embeds.append(embed)

        # 一次回傳多個 Embed
        await interaction.response.send_message(embeds=embeds, ephemeral=False)

    except Exception as e:
        await interaction.response.send_message(f"查詢失敗: {e}", ephemeral=True)

#---------------------------------------------------------------------------------------------------------------------
# 機器人個別指令設定
# 機器人個別指令設定
# 機器人個別指令設定
WEATHER_API_URL = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-091?Authorization={CWA_API_KEY}&format=JSON"

city_choices = [
    app_commands.Choice(name=city, value=city)
    for city in [
        "臺北市", "新北市", "桃園市", "台中市", "台南市", "高雄市",
        "基隆市", "新竹市", "嘉義市", "苗栗縣", "彰化縣", "南投縣",
        "雲林縣", "嘉義縣", "屏東縣", "宜蘭縣", "花蓮縣", "台東縣",
        "澎湖縣", "金門縣", "連江縣"
    ]
]
days_choices = [app_commands.Choice(name=f"{i}天", value=i) for i in range(1, 8)]

# 進度條函式
def progress_bar(value, max_value=100, length=10):
    filled = round(length * value / max_value)
    return f"[{'█' * filled}{'░' * (length - filled)}] {value}%"

# === 針對天氣描述(desc)、降雨機率(pop)、溫度(temp) 做更細的判斷 === #
def get_weather_footer_and_image(desc, pop, temp):
    """
    根據天氣描述(desc)、降雨機率(pop)、平均氣溫(temp)，
    返回 (footer_text, image_url)。
    """

    # 1. 轉換降雨機率與溫度為數字，方便做條件判斷
    try:
        pop_int = int(pop)
    except:
        pop_int = 0
    try:
        temp_int = int(temp)
    except:
        temp_int = 20  # 預設 20 度

    # 2. 先用溫度判斷要不要提醒冷/熱
    temp_msg = ""
    if temp_int < 10:
        temp_msg = "記得多穿一點，天氣真的很冷呢！"
    elif temp_int >= 25:
        temp_msg = "今天好熱呀，出門多補充水分唷！"

    # 3. 判斷「雨」相關邏輯 + pop_int 區間：
    #    - pop_int >= 50：很有可能下雨
    #    - 20 <= pop_int < 50：有點微妙，可能偶爾飄雨
    #    - pop_int < 10：應該不會下雨
    #    （此處可依需求自行再調整區間）
    if any(x in desc for x in ["雨", "降雨", "下雨"]):
        if pop_int >= 50:
            main_msg = "☔下雨機率很高，記得帶把傘出門喔！(ฅ•ω•ฅ)"
            image_url = None
        elif 20 <= pop_int < 50:
            main_msg = "🌧️有點微妙，可能偶爾飄雨，考慮一下要不要帶傘吧(*´ω｀*)"
            image_url = None
        elif pop_int < 10:
            main_msg = "🌥️降雨機率很低，應該不會下雨囉～"
            image_url = None
        else:
            # 如果你還想細分 10~20% 也可以再額外加
            main_msg = "🌦️帶點不確定性，可自行斟酌要不要攜帶雨具～"
            image_url = None
    elif "晴" in desc:
        main_msg = "☀️今天天氣晴朗，真是個好日子"
        image_url = None
    elif any(x in desc for x in ["雲", "陰"]):
        main_msg = "☁️天空陰陰的，要不要帶傘以防萬一呢？(*´ω｀*)"
        image_url = None
    else:
        main_msg = "🌸出門記得注意天氣哦～(ﾉ>ω<)ﾉ"
        image_url = None

    # 4. 整合溫度提示 + 主訊息
    footer_text = main_msg
    if temp_msg:
        footer_text += f" {temp_msg}"
    return footer_text, image_url


weekday_name = ["(一)", "(二)", "(三)", "(四)", "(五)", "(六)", "(日)"]

def fetch_weather_data():
    """
    直接即時抓取 API, 回傳 JSON 物件
    """
    resp = requests.get(WEATHER_API_URL)
    data = resp.json()
    return data

def parse_12h_group_by_day(location_data):
    """
    針對某個特定 'Location' (例如: "臺北市" 的那整塊資料),
    把 'WeatherElement' 下面的所有 12hr 預報, 依據 startTime[:10] (YYYY-MM-DD) 分組
    回傳結構:
    day_dict = {
      "2025-03-16": [ # 該日可能有2筆(06~18, 18~06)
        {
          "start": "2025-03-16 06:00:00",
          "end":   "2025-03-16 18:00:00",
          "平均溫度": "14",
          "最高溫度": "15",
          "最低溫度": "13",
          "最高體感溫度": "14",
          "最低體感溫度": "12",
          "12小時降雨機率": "30",
          "天氣預報綜合描述": "...(長文字)"
          ...
        },
        {
          "start": "2025-03-16 18:00:00",
          "end":   "2025-03-17 06:00:00",
          ...
        }
      ],
      "2025-03-17": [...],
      ...
    }
    """
    day_dict = {}
    weather_elements = location_data["WeatherElement"]

    # 先假設 weather_elements[0]["Time"] 最完整 (實務中需交叉檢查)
    time_slots_num = len(weather_elements[0]["Time"])

    # 建立一個容器: all_slots[i] = {start, end, [各因子]...}
    all_slots = []
    for i in range(time_slots_num):
        slot_info = {}
        slot_info["start"] = weather_elements[0]["Time"][i]["StartTime"]
        slot_info["end"]   = weather_elements[0]["Time"][i]["EndTime"]
        all_slots.append(slot_info)

    # 把所有氣象因子塞進 all_slots
    for w_elem in weather_elements:
        elem_name = w_elem["ElementName"]   # "平均溫度", "天氣現象", ...
        for i, t_slot in enumerate(w_elem["Time"]):
            val_obj = t_slot["ElementValue"][0]
            value = list(val_obj.values())[0]
            all_slots[i][elem_name] = value

    # 依日期分組
    for slot in all_slots:
        date_key = slot["start"][:10]  # "YYYY-MM-DD"
        if date_key not in day_dict:
            day_dict[date_key] = []
        day_dict[date_key].append(slot)
    return day_dict

# 動態選擇 Embed 顏色（依據平均溫度 & 降雨機率做簡易判斷）
def get_embed_color(avg_temp, max_pop):
    """
    根據平均溫度與降雨機率，動態回傳一個顏色值 (int)。
    這裡僅示範簡單的邏輯，可依實際需求自行調整。
    """
    # 先將溫度、降雨機率都轉為 int
    try:
        t = int(avg_temp)
    except:
        t = 20  # 預設溫度
    try:
        p = int(max_pop)
    except:
        p = 0   # 預設降雨機率

    # 若降雨機率很高，偏藍
    if p >= 70:
        return 0x0000FF  # 藍
    # 若天氣炎熱
    elif t >= 25:
        return 0xFF4500  # 橘紅
    # 若溫暖舒適
    elif t >= 20:
        return 0xFFA500  # 橘
    # 其餘涼爽
    else:
        return 0x00BFFF  # 淺藍

@bot.tree.command(name="weather", description="7日內天氣預報")
@app_commands.describe(city="查詢縣市", days="顯示天數(1~7)")
@app_commands.choices(city=city_choices, days=days_choices)
async def weather_command(interaction: discord.Interaction, city: app_commands.Choice[str], days: app_commands.Choice[int]):
    # 1) 即時抓取天氣資料
    try:
        raw_data = fetch_weather_data()
    except Exception as e:
        await interaction.response.send_message(f"抓取氣象資料失敗：{e}", ephemeral=True)
        return

    # 2) 找到對應 city 的 location_data
    try:
        all_locations = raw_data["records"]["Locations"][0]["Location"]
    except:
        await interaction.response.send_message("JSON 結構異常", ephemeral=True)
        return
    
    city_name = city.value.replace("台", "臺")

    location_data = None
    for loc in all_locations:
        if loc["LocationName"] == city_name:
            location_data = loc
            break

    if not location_data:
        await interaction.response.send_message(f"⚠️ 查無 {city.value}（或 {city_name} ） 天氣資料！", ephemeral=True)
        return

    # 3) 解析: 「同一天」的多個12小時時段 => day_dict
    day_dict = parse_12h_group_by_day(location_data)

    # 4) 挑出日期並排序，只顯示使用者指定的 n_days
    sorted_dates = sorted(day_dict.keys())[: days.value]
    if not sorted_dates:
        await interaction.response.send_message("沒有可顯示的天氣資料！", ephemeral=True)
        return

    # 5) 針對每個日期做 1 個 Embed
    embeds = []
    for date_str in sorted_dates:
        slot_list = day_dict[date_str]
        slot_list = sorted(slot_list, key=lambda s: s["start"])  # 按 startTime 排序

        # 只保留想要顯示的欄位
        temp_field      = ""  # 🌡️溫度(°C)
        temp_at_field   = ""  # 😌體感溫度(°C)
        pop12_field     = ""  # 💧12小時降雨機率
        desc_field      = ""  # 📝天氣描述

        # 用來動態計算平均溫度 / 最大降雨機率
        temp_list = []
        pop_list = []

        for s in slot_list:
            start_hhmm = s["start"][11:16]
            end_hhmm   = s["end"][11:16]
            period_title = f"{start_hhmm} ~ {end_hhmm}"

            # 🌡️溫度(°C)
            avgT = s.get("平均溫度", "N/A")
            maxT = s.get("最高溫度", "N/A")
            minT = s.get("最低溫度", "N/A")

            # 嘗試轉為 int 以計算平均溫度
            try:
                temp_list.append(int(avgT))
            except:
                pass

            temp_field += (
                f"**{period_title}**\n"
                f"平均：{avgT}°C\n"
                f"最高：{maxT}°C\n"
                f"最低：{minT}°C\n\n"
            )

            # 😌體感溫度(°C)
            maxAT = s.get("最高體感溫度", "N/A")
            minAT = s.get("最低體感溫度", "N/A")
            temp_at_field += (
                f"**{period_title}**\n"
                f"最高：{maxAT}°C\n"
                f"最低：{minAT}°C\n\n"
            )

            # 💧12小時降雨機率 + 進度條
            pop12 = s.get("12小時降雨機率", "N/A")
            try:
                pop_list.append(int(pop12))
                pop_bar = progress_bar(int(pop12), 100, 10)
            except:
                pop_bar = "[無法顯示]"
            pop12_field += (
                f"**{period_title}**\n"
                f"{pop_bar}\n\n"
            )

            # 📝天氣描述
            desc = s.get("天氣預報綜合描述", "N/A")
            desc_field += (
                f"**{period_title}**\n"
                f"{desc}\n\n"
            )

        # 計算當天的「平均溫度」和「最大降雨機率」，以便決定 Embed 顏色 & Footer
        daily_avg_temp = sum(temp_list) / len(temp_list) if temp_list else 20
        daily_max_pop = max(pop_list) if pop_list else 0

        # 取得週幾標籤
        try:
            from datetime import datetime
            dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
            weekday_idx = dt_obj.weekday()  # Monday=0, Sunday=6
            weekday_label = weekday_name[weekday_idx]
        except:
            weekday_label = ""

        # 建立 Embed（動態顏色）
        embed_color = get_embed_color(daily_avg_temp, daily_max_pop)
        embed = discord.Embed(
            title=f"{location_data['LocationName']} | 📅 {date_str} {weekday_label} 天氣預報",
            color=embed_color
        )
        embed.add_field(
            name="🌡️溫度(°C)",
            value=temp_field if temp_field else "N/A",
            inline=True
        )
        embed.add_field(
            name="😌體感溫度(°C)",
            value=temp_at_field if temp_at_field else "N/A",
            inline=True
        )
        embed.add_field(
            name="💧12小時降雨機率",
            value=pop12_field if pop12_field else "N/A",
            inline=True
        )
        # 移除其餘不想顯示的欄位
        embed.add_field(
            name="📝天氣描述",
            value=desc_field if desc_field else "N/A",
            inline=False
        )

        # 針對當天的天氣描述設定 footer 與縮圖
        # 這裡抓「第一個時段」作為當天描述的代表，也可自行調整策略
        first_slot_desc = slot_list[0].get("天氣預報綜合描述", "") if slot_list else ""
        footer_text, weather_image = get_weather_footer_and_image(
            first_slot_desc,
            daily_max_pop,         # 傳當天最大降雨機率
            daily_avg_temp         # 傳當天平均溫度
        )
        embed.set_footer(text=footer_text)
        embed.set_thumbnail(url=weather_image)

        embeds.append(embed)

    # 6) 回覆
    await interaction.response.send_message(embed=embeds[0])
    for e in embeds[1:]:
        await interaction.followup.send(embed=e)

#---------------------------------------------------------------------------------------------------------------------
# 機器人個別指令設定
# @bot.tree.command(name="speak_ja", description="生成語音(日文)")
# async def read(interaction: discord.Interaction, *, text: str):
#     await interaction.response.defer()
    
#     data = {
#         "text": text,
#         "text_language": "ja"
#     }
    
#     try:
#         response = requests.post("http://127.0.0.1:9880", json=data)
        
#         if response.status_code == 400:
#             await interaction.followup.send(f"Error: {response.json().get('message')}")
#             return
        
#         audio_file_path = 'output.wav'
#         with open(audio_file_path, 'wb') as f:
#             f.write(response.content)
        
#         await interaction.followup.send(file=discord.File(audio_file_path))
    
#     except Exception as e:
#         await interaction.followup.send(f"出錯: {e}")

#---------------------------------------------------------------------------------------------------------------------
# 機器人個別指令設定
 # @bot.tree.command(name="speak_zh", description="生成語音(中文)")
# async def read(interaction: discord.Interaction, *, text: str):
#     await interaction.response.defer()
    
#     data = {
#         "text": text,
#         "text_language": "zh"
#     }
    
#     try:
#         response = requests.post("http://127.0.0.1:9881", json=data)
        
#         if response.status_code == 400:
#             await interaction.followup.send(f"Error: {response.json().get('message')}")
#             return
        
#         audio_file_path = 'output.wav'
#         with open(audio_file_path, 'wb') as f:
#             f.write(response.content)
        
#         await interaction.followup.send(file=discord.File(audio_file_path))
    
#     except Exception as e:
#         await interaction.followup.send(f"出錯: {e}")

#---------------------------------------------------------------------------------------------------------------------
# 畫圖修圖相關
# DALL·E 3 繪圖函式
def _blocking_dalle3_image(prompt: str):
    client = openai.Client(api_key=OPENAI_API_KEY)
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="hd",
        n=1,
    )
    return response

# Gemini 圖像生成函式
def _blocking_gemini_image(prompt: str):
    client = genai.Client(api_key=GOOGLE_API_KEY)
    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["Text", "Image"]
        )
    )
    # 提取圖片資料
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            image_data = part.inline_data.data
            image = Image.open(BytesIO(image_data))
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            return buffer
    return None

# Gemini 修圖功能：輸入圖片與指令後生成新圖
async def _edit_image_with_gemini(prompt: str, image_bytes: bytes):
    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        image = Image.open(BytesIO(image_bytes))
        
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=[prompt, image],
            config=types.GenerateContentConfig(
                response_modalities=["Text", "Image"]
            )
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                edited_image = Image.open(BytesIO(part.inline_data.data))
                buffer = BytesIO()
                edited_image.save(buffer, format="PNG")
                buffer.seek(0)
                return buffer
        return None
    except Exception as e:
        print(f"錯誤：{e}")
        return f"本來就不穩的Gemini修圖功能回傳錯誤：{e}"

# Discord指令
@bot.tree.command(name="draw", description="畫圖")
@app_commands.describe(model="選擇畫圖模型", prompt="輸入提示詞")
@app_commands.choices(
    model=[
        app_commands.Choice(name="DALL-E-3", value="dall-e-3"),
        app_commands.Choice(name="Gemini-3-pro", value="gemini-3-pro-image-preview")
    ]
)
async def draw(interaction: discord.Interaction, model: app_commands.Choice[str], prompt: str):
    await interaction.response.defer()

    try:
        if model.value == "dall-e-3":
            response = await asyncio.to_thread(_blocking_dalle3_image, prompt)
            if not response or not response.data or not response.data[0].url:
                await interaction.followup.send("無法取得圖像")
                return
            image_url = response.data[0].url
            embed = discord.Embed(title="DALL-E-3 好ㄌ", color=0xFCAF17)
            embed.set_image(url=image_url)
            await interaction.followup.send(embed=embed)

        elif model.value == "gemini-3-pro-image-preview":
            image_buffer = await asyncio.to_thread(_blocking_gemini_image, prompt)
            if image_buffer is None:
                await interaction.followup.send("無法取得圖像")
                return
            file = discord.File(fp=image_buffer, filename="gemini_image.png")
            embed = discord.Embed(title="Gemini-3-pro 好ㄌ", color=0xFCAF17)
            embed.set_image(url="attachment://gemini_image.png")
            await interaction.followup.send(embed=embed, file=file)

        else:
            await interaction.followup.send("未知模型")

    except Exception as e:
        error_message = str(e)
        await interaction.followup.send(f"錯誤：{error_message}")
        print(f"錯誤: {error_message}")

#---------------------------------------------------------------------------------------------------------------------
# 每日通知
async def send_daily_notification():
    await bot.wait_until_ready()  # 確保機器人已準備就緒
    channel = bot.get_channel(channel_id)
    
    if channel is None:
        print(f"無法獲取頻道 {channel_id}")
        return
    else:
        print(f"成功獲取到頻道 {channel_id}")
    
    while not bot.is_closed():
        now = datetime.datetime.now()
        target_time = now.replace(hour=6, minute=0, second=0, microsecond=0)  # 設置目標時間

        if now > target_time:  # 如果當前時間已經超過目標時間，調整目標時間為明天
            target_time += datetime.timedelta(days=1)
        
        wait_time = (target_time - now).total_seconds()
        print(f"當前時間: {now}, 目標每日時間: {target_time}")
        await asyncio.sleep(wait_time)

        # 創建嵌入消息
        embed = discord.Embed(
            title="你說的對，但是",
            description="🎶月火水木金土日🎶🎶毎日がHoliday🎶",
            color=0xFCAF17  
        )
        
        # 設置目標圖片文件夾路徑並隨機選取圖片
        image_folder = str(MEDIA_ROOT / "daily")
        image_files = [file for file in os.listdir(image_folder) if file.endswith(('png', 'jpg', 'jpeg', 'gif'))]

        if image_files:
            random_image = random.choice(image_files)
            image_path = os.path.join(image_folder, random_image)

            # 發送嵌入消息和本地圖片
            with open(image_path, 'rb') as f:
                picture = discord.File(f, filename=random_image)
                embed.set_image(url=f"attachment://{random_image}")  # 設定圖片引用為本地文件
                await channel.send(embed=embed, file=picture)

# 花帆通知
is_running = False
last_notification_date = None

async def send_kaho_notification():
    global is_running, last_notification_date

    if is_running:
        print("通知運行中，跳過啟動")
        return

    is_running = True
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)

    if channel is None:
        print(f"無法獲取頻道 {channel_id}")
        is_running = False
        return
    else:
        print(f"成功獲取到頻道 {channel_id}")

    try:
        while not bot.is_closed():
            now = datetime.datetime.now()
            today_date = now.date()

            # 檢查是否已在當天發送過通知
            if last_notification_date == today_date:
                # 計算到明天凌晨的等待時間
                tomorrow = (now + datetime.timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                wait_seconds = (tomorrow - now).total_seconds()
                print(f"今天已發送通知，等待至：{tomorrow}")
                await asyncio.sleep(wait_seconds)
                continue

            # 如果今天還未發送，生成今日的隨機時間
            if last_notification_date != today_date:
                random_hour = random.randint(0, 23)
                random_minute = random.randint(0, 59)
                target_time = now.replace(
                    hour=random_hour,
                    minute=random_minute,
                    second=0,
                    microsecond=0
                )

                # 如果生成的時間已經過了，改為明天
                if now > target_time:
                    target_time += datetime.timedelta(days=1)

                wait_time = (target_time - now).total_seconds()
                print(f"當前時間: {now}, 目標花帆時間：{target_time}")
                await asyncio.sleep(wait_time)

                # 發送花帆圖片
                image_folder = str(MEDIA_ROOT / "kaho")
                image_files = [file for file in os.listdir(image_folder) if file.lower().endswith(('png', 'jpg', 'jpeg', 'gif'))]

                if image_files:
                    random_image = random.choice(image_files)
                    image_path = os.path.join(image_folder, random_image)

                    embed = discord.Embed(
                        title="每日可愛花帆",
                        description="",
                        color=0xFCAF17
                    )

                    with open(image_path, 'rb') as f:
                        picture = discord.File(f, filename=random_image)
                        embed.set_image(url=f"attachment://{random_image}")
                        await channel.send(embed=embed, file=picture)

                # 更新最後發送日期
                last_notification_date = today_date
                print(f"通知已發送，更新日期為：{last_notification_date}")

    except Exception as e:
        print(f"發生錯誤: {e}")
        is_running = False
    finally:
        is_running = False

async def send_201_notification():
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)

    if channel is None:
        print(f"無法獲取頻道 {channel_id}")
        return
    else:
        print(f"成功獲取到頻道 {channel_id}")

    while not bot.is_closed():
        # 取得目前時間
        now = datetime.datetime.now()

        # 設定目標時間：每天的 2:01
        target_time = now.replace(hour=2, minute=1, second=0, microsecond=0)

        # 如果當前時間已經超過當天 2:01，則目標改為明天
        if now > target_time:
            target_time += datetime.timedelta(days=1)

        # 計算需要等待的秒數
        wait_time = (target_time - now).total_seconds()
        print(f"當前時間: {now}, 目標希介時間: {target_time}")
        await asyncio.sleep(wait_time)

        # 時間到了就發送訊息
        await channel.send("201")

daily_notification_started = False
kaho_notification_started = False
_201_notification_started = False


def standardize_url(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc

    if 'pixiv.net' in domain or 'pximg.net' in domain:
        return standardize_pixiv_url(url)
    elif 'danbooru.donmai.us' in domain:
        return standardize_danbooru_url(url)
    elif 'gelbooru.com' in domain:
        return standardize_gelbooru_url(url)
    elif 'yande.re' in domain:
        return standardize_yandere_url(url)
    
    return url

def standardize_pixiv_url(url):
    # 提取作品ID
    pixiv_id = extract_pixiv_id(url)
    if pixiv_id:
        return f"https://www.pixiv.net/artworks/{pixiv_id}"
    return url

def standardize_danbooru_url(url):
    danbooru_id = extract_danbooru_id(url)
    if danbooru_id:
        return f"https://danbooru.donmai.us/posts/{danbooru_id}"
    return url

def standardize_gelbooru_url(url):
    gelbooru_id = extract_gelbooru_id(url)
    if gelbooru_id:
        return f"https://gelbooru.com/index.php?page=post&s=view&id={gelbooru_id}"
    return url

def standardize_yandere_url(url):
    yandere_id = extract_yandere_id(url)
    if yandere_id:
        return f"https://yande.re/post/show/{yandere_id}"
    return url

def extract_pixiv_id(url):
    patterns = [
        r"illust_id=(\d+)",  # 針對帶有illust_id參數的連結
        r"artworks/(\d+)",   # 針對artworks頁面的連結
        r"/(\d+)_p\d+\.jpg",  # 針對圖片連結（如 i.pximg.net 圖片伺服器上的圖片）
        r"/(\d+)_p\d+_master1200\.jpg",  # master1200 圖片格式
        r"/img/\d+/\d+/\d+/\d+/\d+/\d+/(\d+)"  # 針對 i.pximg.net 的 URL 路徑結構
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def extract_danbooru_id(url):
    match = re.search(r"posts/(\d+)", url)
    return match.group(1) if match else None

def extract_gelbooru_id(url):
    match = re.search(r"id=(\d+)", url)
    return match.group(1) if match else None

def extract_yandere_id(url):
    match = re.search(r"post/show/(\d+)", url)
    return match.group(1) if match else None

def extract_site_name(url):
    domain_map = {
        'pixiv.net': 'Pixiv',
        'pximg.net': 'Pixiv',
        'danbooru.donmai.us': 'Danbooru',
        'gelbooru.com': 'Gelbooru',
        'yande.re': 'Yande.re',
        'twitter.com': 'Twitter',
        'x.com': 'X',
        'anidb.net':'AniDB',
        'skeb.jp':'skeb',
        'deviantart.com':'DeviantArt',
    }
    
    parsed_url = urlparse(url)
    domain = parsed_url.netloc

    for known_domain, site_name in domain_map.items():
        if known_domain in domain:
            return site_name
    
    return None

async def search_image(image_url):
    params = {
        'db': 999,
        'output_type': 2,
        'testmode': 1,
        'numres': 1,
        'api_key': SAUCENAO_API_KEY,
        'url': image_url
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('https://saucenao.com/search.php', params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Error: Received status code {response.status}")
                    return {'error': '搜圖錯誤(30秒4次only)'}
        except Exception as e:
            print(f"Exception occurred: {e}")
            return {'error': 'API請求失敗'}

async def send_embed_results(message, results):
#    key_mapping = {
#        'title': '標題',
#        'part': '集數',
#        'author_name': '創作者',
#        'author_url': '作者連結',
#        'pixiv_id': 'P站ID',
#        'member_name': '會員名',
#        'member_id': '會員ID',
#        'source': '來源',
#        'year': '年份',
#        'est_time': '出現時間',
#        'created_at': '創建時間',
#        'tweet_id': '推文ID',
#        'twitter_user_id': 'X ID',
#        'twitter_user_handle': 'X名',
#        'creator': '創作者',
#        'material': '作品',
#        'characters': '角色',
#        'danbooru_id': 'Danbooru ID',
#        'gelbooru_id': 'Gelbooru ID',
#        'yandere_id': 'Yandere ID',
#        'eng_name': '英文名',
#        'jp_name': '日文名'
#    }

    if 'error' in results:
        await message.channel.send(results['error'])
        return

    for result in results.get('results', []):
        embed = Embed(title="搜圖結果", color=0xFCAF17)
        header = result.get('header', {})
        data = result.get('data', {})

        # 顯示縮略圖
        if 'thumbnail' in header:
            embed.set_thumbnail(url=header['thumbnail'])

        embed.add_field(name="相似度", value=header.get('similarity', 'N/A') + '%', inline=True)
        await message.channel.send(embed=embed)

        # 構建詳細的文字內容
        text_content = "## 詳細資料:\n\n"

        # 顯示所有可用的數據
        if 'source' in data:
            # 標準化來源連結
            standardized_source = standardize_url(data['source'])
            text_content += f"**來源**: {standardized_source}\n"

        if 'title' in data:
            text_content += f"**標題**: {data['title']}\n"
        if 'part' in data:
            text_content += f"**集數**: {data['part']}\n"
        if 'author_name' in data:
            text_content += f"**作者**: {data['author_name']}\n"
        if 'pixiv_id' in data:
            text_content += f"**P站ID**: {data['pixiv_id']}\n"
        if 'member_name' in data:
            text_content += f"**會員名**: {data['member_name']}\n"
        if 'member_id' in data:
            text_content += f"**會員ID**: {data['member_id']}\n"
        if 'year' in data:
            text_content += f"**年份**: {data['year']}\n"
        if 'est_time' in data:
            text_content += f"**出現時間**: {data['est_time']}\n"
        if 'created_at' in data:
            text_content += f"**創建時間**: {data['created_at']}\n"
        if 'tweet_id' in data:
            text_content += f"**推文ID**: {data['tweet_id']}\n"
        if 'twitter_user_id' in data:
            text_content += f"**X ID**: {data['twitter_user_id']}\n"
        if 'twitter_user_handle' in data:
            text_content += f"**X名**: {data['twitter_user_handle']}\n"
        if 'creator' in data:
            text_content += f"**畫師**: {data['creator']}\n"
        if 'material' in data:
            text_content += f"**作品**: {data['material']}\n"
        if 'characters' in data:
            text_content += f"**角色**: {data['characters']}\n"
        if 'danbooru_id' in data:
            text_content += f"**Danbooru ID**: {data['danbooru_id']}\n"
        if 'gelbooru_id' in data:
            text_content += f"**Gelbooru ID**: {data['gelbooru_id']}\n"
        if 'yandere_id' in data:
            text_content += f"**Yandere ID**: {data['yandere_id']}\n"
        if 'eng_name' in data:
            text_content += f"**英文名**: {data['eng_name']}\n"
        if 'jp_name' in data:
            text_content += f"**日文名**: {data['jp_name']}\n"

        # 處理外部連結
        if 'ext_urls' in data:
            ext_urls = data['ext_urls']
            standardized_urls = [standardize_url(url) for url in ext_urls]
            
            if len(standardized_urls) == 1:
                primary_url = standardized_urls[0]
                site_name = extract_site_name(primary_url)
                text_content += f"**連結**: [{site_name}]({primary_url})\n"
            else:
                text_content += "**連結**:\n"
                for url in standardized_urls:
                    site_name = extract_site_name(url)
                    if site_name:
                        text_content += f"- [{site_name}]({url})\n"
                    else:
                        text_content += f"- <{url}>\n"

        # 發送詳細內容
        if text_content:
            await message.channel.send(text_content)

#---------------------------------------------------------------------------------------------------------------------
# ?聽設定語音轉錄
client_ai = OpenAI()
AUDIO_MAX = 25 * 1024 * 1024              # 25 MB 上限
PROMPT_MAX = 800                          # 最長字元數，避免 prompt 過長
DEFAULT_LISTEN_PROMPT = (
    "忠實逐字轉錄此段語音，保留所有語氣詞與填充詞，並使用標點符號和換行分段。"
)
SUPPORTED_EXTS = ("mp3", "mp4", "m4a", "mpeg", "mpga", "webm", "wav", "ogg")

def convert_ogg_to_mp3(data: bytes, src_name: str = "audio.ogg") -> Tuple[Optional[bytes], str]:
    """OGG+Opus ➜ MP3；回傳 (bytes or None, new_filename)."""
    new_name = os.path.splitext(src_name)[0] + ".mp3"
    try:
        if _PYDUB:
            audio = AudioSegment.from_file(io.BytesIO(data), format="ogg")
            buf = io.BytesIO()
            audio.export(buf, format="mp3", bitrate="192k")
            buf.seek(0)
            mp3_bytes = buf.read()
            return (mp3_bytes if mp3_bytes else None, new_name)
        # ffmpeg fallback
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_in:
            tmp_in.write(data)
            in_name = tmp_in.name
        out_fd, out_name = tempfile.mkstemp(suffix=".mp3")
        os.close(out_fd)
        try:
            subprocess.check_call([
                "ffmpeg", "-y", "-i", in_name,
                "-codec:a", "libmp3lame", "-qscale:a", "2", out_name,
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with open(out_name, "rb") as f:
                mp3_bytes = f.read()
                return (mp3_bytes if mp3_bytes else None, new_name)
        finally:
            os.unlink(in_name)
            os.unlink(out_name)
    except Exception as e:
        print(f"[convert_ogg_to_mp3] 轉檔失敗: {e}")
        return (None, new_name)

async def call_transcribe(data: bytes,
                          filename: str,
                          model: str = "gpt-4o-transcribe",
                          prompt: str | None = None) -> str:
    try:
        buf = io.BytesIO(data)
        buf.name = filename                    # 讓 SDK 得到正確副檔名
        resp = await asyncio.to_thread(
            client_ai.audio.transcriptions.create,
            model=model,
            file=buf,
            response_format="text",
            prompt=prompt,
        )
        # -------- 型別兼容處理 --------
        if isinstance(resp, str):              # gpt‑4o‑transcribe / gpt‑4o‑mini‑transcribe
            return resp.strip()
        # whisper‑1 若 response_format="text" 也會給 str；
        # 若選 "json"/"verbose_json" 會得到 dict
        return str(resp).strip()
    except APITimeoutError:
        return "[OpenAI Timeout: 請稍後再試]"
    except APIError as e:
        return f"[OpenAI Error] {e}"

def parse_listen_prompt(raw: str) -> Optional[str]:
    content = re.sub(r"^[?？]聽", "", raw, count=1).strip()
    if not content:
        return DEFAULT_LISTEN_PROMPT
    m = re.match(r'[「"“](.+?)[」"”]$', content)
    prompt = m.group(1).strip() if m else content
    return prompt[:PROMPT_MAX] if len(prompt) > PROMPT_MAX else prompt

async def process_audio_attachment(att: discord.Attachment) -> Tuple[Optional[bytes], str]:
    """回傳 (audio_bytes or None, filename)"""
    if att.size > AUDIO_MAX:
        return (None, att.filename)
    ext = att.filename.lower().split(".")[-1]
    data = await att.read()
    if ext == "ogg":
        return convert_ogg_to_mp3(data, att.filename)
    elif ext in SUPPORTED_EXTS:
        return (data, att.filename)
    return (None, att.filename)

#---------------------------------------------------------------------------------------------------------------------
@bot.event
async def on_ready():
    global daily_notification_started, kaho_notification_started, _201_notification_started

    activity = discord.Game(name="蓮ノ空女學院")
    await bot.change_presence(activity=activity)

    if not auto_check_earthquake.is_running():
        auto_check_earthquake.start()

    slash = await bot.tree.sync()
    print(f"目前登入身份 --> {bot.user}")
    print(f"載入 {len(slash)} 個斜線指令")

    # 啟動每日通知，僅執行一次
    if not daily_notification_started:
        bot.loop.create_task(send_daily_notification())
        daily_notification_started = True

    if not kaho_notification_started:
        bot.loop.create_task(send_kaho_notification())
        kaho_notification_started = True

    if not _201_notification_started:
        bot.loop.create_task(send_201_notification())
        _201_notification_started = True
    
#---------------------------------------------------------------------------------------------------------------------
# 機器人監聽對話活動設定
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    #統一訊息內容格式化：處理全形空格、多重空格
    message.content = re.sub(r'\s+', ' ', message.content.replace('　', ' ')).strip()

    #處理 SaucyBot 內嵌訊息刪除
    if message.author.id == SAUCYBOT_ID and message.embeds:
        try:
            await message.delete()
            print("成功刪除 SaucyBot 的嵌入訊息")
        except discord.errors.NotFound:
            print("訊息已不存在，無法刪除")
        except discord.errors.Forbidden:
            print("權限不足，無法刪除 SaucyBot 的訊息")
        except Exception as e:
            print(f"刪除 SaucyBot 訊息時發生錯誤: {e}")
        return

    # 轉錄
    if re.match(r"[?？]聽", message.content):
        prompt_txt = parse_listen_prompt(message.content)
        if not message.attachments:
            await message.channel.send("語音呢 (≤ 25 MB)。")
            return

        for att in message.attachments:
            if not any(att.filename.lower().endswith(ext) for ext in SUPPORTED_EXTS):
                await message.channel.send(f"不支援的格式：{att.filename}")
                continue

            data, fname = await process_audio_attachment(att)
            if data is None:
                await message.channel.send(f"`{att.filename}` 處理失敗或超過 25 MB。")
                continue

            async with message.channel.typing():
                text = await call_transcribe(data, fname, prompt=prompt_txt)

            header = "**好ㄌ**：\n\n" if prompt_txt else ""
            await send_in_chunks(message.channel, text, prefix=header)
        return
    
    # 搜圖
    if message.content.startswith('?圖') or message.content.startswith('？圖'):
        if message.attachments:
            for attachment in message.attachments:
                if any(attachment.filename.lower().endswith(ext) for ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']):
                    image_url = attachment.url
                    print(f'Image URL: {image_url}')
                    results = await search_image(image_url)
                    if isinstance(results, str):
                        await message.channel.send(results)
                    else:
                        await send_embed_results(message, results)
            return
        await message.channel.send('圖呢?')

    # 讀圖分析
    elif message.content.startswith('?看') or message.content.startswith('？看'):
        content = message.content[2:].strip()
        if not content:
            content = ("詳細描述此圖，若有文字就翻譯成繁體中文並全部寫出")

        used_image_model = current_image_model

        async def analyse_and_reply(image_url: str):
            print(f'Image URL: {image_url}')

            # --- 準備回饋訊息的前綴 (修改點) ---
            prefix = f"目前模型: **{used_image_model}**\n"
            response = ""

            if used_image_model == "GPT-5.1":
                # 為 GPT-5 加上額外的設定資訊
                prefix += f"推理強度: **{gpt51_image_reasoning_effort}**\n"
                prefix += f"詳細程度: **{gpt51_image_verbosity}**\n\n"
                
                # 呼叫函式時，傳入儲存好的設定
                response = await GPT51_image_response(
                    image_url, 
                    text=content, 
                    reasoning_effort=gpt51_image_reasoning_effort, 
                    verbosity=gpt51_image_verbosity
                )
            elif used_image_model == "Gemini-3-Pro":
                response = await gemini_image_response(image_url, text=content)
            else:
                response = "沒選到讀圖模型"

            # 將前綴和回應組合起來
            response_text = prefix + response
            
            embed = discord.Embed(title="圖片分析結果", color=0xFCAF17)
            embed.set_thumbnail(url=image_url)
            await message.channel.send(embed=embed)
            await send_in_chunks(message.channel, response_text) # 傳送組合後的回應

        # ── 處理附件 ──
        if message.attachments:
            for attachment in message.attachments:
                if any(attachment.filename.lower().endswith(ext) for ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']):
                    await analyse_and_reply(attachment.url)
            return

        # ── 處理 URL 文字 ──
        elif content.startswith('http'):
            await analyse_and_reply(content)
        else:
            await message.channel.send('圖呢?')

    # 修圖
    elif message.content.startswith('?修圖') or message.content.startswith('？修圖'):
        prompt = message.content[3:].strip()
        if not prompt:
            await message.channel.send("附加打字說明怎修")
            return

        # 強化 prompt：若太短則補上完整提示
        if len(prompt) < 8:
            prompt += "，請幫我自然修改並產生圖片。"
        else:
            prompt += "。請產生圖片。"

        if message.attachments:
            for attachment in message.attachments:
                if any(attachment.filename.lower().endswith(ext) for ext in ['jpg', 'jpeg', 'png']):
                    image_bytes = await attachment.read()
                    image_buffer = await _edit_image_with_gemini(prompt, image_bytes)

                    if isinstance(image_buffer, str):
                        await message.channel.send(image_buffer)  # 顯示錯誤訊息
                    elif image_buffer:
                        if image_buffer:
                            filename = "edited.png"
                            file = discord.File(fp=image_buffer, filename=filename)

                            embed = discord.Embed(
                                title="Gemini-3-pro 好ㄌ(不穩，英文簡中效果最好)",
                                description=f"Prompt: {prompt}",
                                color=0xFCAF17
                            )
                            embed.set_image(url=f"attachment://{filename}")

                        await message.channel.send(embed=embed, file=file)
                    else:
                        await message.channel.send("修圖失敗，再試一次")
                    return
        await message.channel.send("圖呢？")

    # ?n / ?w / ?jm / ?p 
    elif message.content.startswith('?n') or message.content.startswith('？n'):
        code = message.content[2:].strip()
        if code.isdigit() and (5 <= len(code) <= 6):
            await message.channel.send(f'https://nhentai.net/g/{code}/')
        else:
            await message.channel.send('無效神諭')

    elif message.content.startswith('?w') or message.content.startswith('？w'):
        code = message.content[2:].strip()
        if code.isdigit() and (5 <= len(code) <= 6):
            await message.channel.send(f'https://www.wnacg.com/photos-slist-aid-{code}.html')
        else:
            await message.channel.send('無效神諭')

    elif message.content.startswith('?jm') or message.content.startswith('？jm'):
        code = message.content[3:].strip()
        if code.isdigit() and (5 <= len(code) <= 6):
            await message.channel.send(f'https://jmcomic.me/album/{code}/')
        else:
            await message.channel.send('無效神諭')

    elif message.content.startswith('?p') or message.content.startswith('？p'):
        code = message.content[2:].strip()
        if code.isdigit() and (8 <= len(code) <= 9):
            await message.channel.send(f'https://www.pixiv.net/artworks/{code}')
        else:
            await message.channel.send('無效神諭')

bot.run(TOKEN)
