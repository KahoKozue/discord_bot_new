import os
import aiohttp
import random
import discord
import re
import openai
from openai import OpenAI
from discord import Intents, Embed, app_commands
from discord.ext import commands
from dotenv import load_dotenv

#---------------------------------------------------------------------------------------------------------------------

# Load .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
SAUCENAO_API_KEY = os.getenv('SAUCENAO_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not TOKEN:
    print(".env沒找到Discord token")
if not SAUCENAO_API_KEY:
    print(".env沒找到SauceNAO API key")
if not OPENAI_API_KEY:
    print(".env沒找到OpenAI API key")

#---------------------------------------------------------------------------------------------------------------------

openai.api_key = OPENAI_API_KEY

intents = Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

current_model = "GPT4o"
conversation_history = {}

#---------------------------------------------------------------------------------------------------------------------

def GPT3t_response(text, user_id):
    client = openai.Client(api_key=OPENAI_API_KEY)
    
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    
    conversation_history[user_id].append({"role": "user", "content": text})
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=conversation_history[user_id][-5:],  # 只發最近的 5 條對話記錄
        temperature=1,
        max_tokens=4096,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    
    answer = response.choices[0].message.content
    conversation_history[user_id].append({"role": "assistant", "content": answer})
    
    return answer

def GPT4o_response(text, user_id):
    client = openai.Client(api_key=OPENAI_API_KEY)
    
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    
    conversation_history[user_id].append({"role": "user", "content": text})
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=conversation_history[user_id][-5:],  # 只發最近的 5 條對話記錄
        temperature=1,
        max_tokens=4096,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    
    answer = response.choices[0].message.content
    conversation_history[user_id].append({"role": "assistant", "content": answer})
    
    return answer

def GPT4o_image_response(image_url, user_id):
    client = openai.Client(api_key=OPENAI_API_KEY)
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "這張圖是什麼"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
                    },
                },
            ],
        }
    ]
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=4096,
    )
    
    answer = response.choices[0].message.content
    return answer

def GPT4t_response(text, user_id):
    client = openai.Client(api_key=OPENAI_API_KEY)
    
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    
    conversation_history[user_id].append({"role": "user", "content": text})
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=conversation_history[user_id][-5:],  # 只發最近的 5 條對話記錄
        temperature=1,
        max_tokens=4096,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    
    answer = response.choices[0].message.content
    conversation_history[user_id].append({"role": "assistant", "content": answer})
    
    return answer

#---------------------------------------------------------------------------------------------------------------------

@bot.tree.command(name="chat", description="喜多喜多")
async def chat(interaction: discord.Interaction, message: str):
    await interaction.response.defer()  # 延長響應時間
    user_id = interaction.user.id
    
    if current_model == "GPT3t":
        response = GPT3t_response(message, user_id)
    elif current_model == "GPT4o":
        response = GPT4o_response(message, user_id)
    else:
        response = GPT4t_response(message, user_id)
    
    await interaction.followup.send(f"目前模型: {current_model}\n\n{response}")

#---------------------------------------------------------------------------------------------------------------------

@bot.tree.command(name="chat_model", description="切換模型")
@app_commands.choices(choices=[
    app_commands.Choice(name="GPT-3.5-turbo", value="GPT3t"),
    app_commands.Choice(name="GPT-4o", value="GPT4o"),
    app_commands.Choice(name="GPT-4-turbo", value="GPT4t"),
])
async def chat_model(interaction: discord.Interaction, choices: app_commands.Choice[str]):
    global current_model
    current_model = choices.value
    await interaction.response.send_message(f"已切換到模型：{choices.name}")

#---------------------------------------------------------------------------------------------------------------------

@bot.tree.command(name="reset", description="重製上下文")
async def clear(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    if user_id in conversation_history:
        conversation_history[user_id] = []
        await interaction.response.send_message("上下文已重製。")
    else:
        await interaction.response.send_message("無上下文。")

#---------------------------------------------------------------------------------------------------------------------

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

@bot.tree.command(name="draw", description="用DALL·E 3畫圖")
async def draw(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()  # 延遲回應,讓用戶知道正在處理請求

    client = OpenAI()
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url

    embed = discord.Embed(title="畫好ㄌ", color=0x1e90ff)
    embed.set_image(url=image_url)
    await interaction.followup.send(embed=embed)

#---------------------------------------------------------------------------------------------------------------------

# 偵測詞和對應回應
reply_dict = {
    "幹": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\1.jpg",
            "E:\\eric2\\discord_bot_output\\images\\4.jpg",
            "E:\\eric2\\discord_bot_output\\images\\7.jpg",
            "E:\\eric2\\discord_bot_output\\images\\8.jpg",
            "E:\\eric2\\discord_bot_output\\images\\10.jpg",
            "E:\\eric2\\discord_bot_output\\images\\11.jpg",
            "E:\\eric2\\discord_bot_output\\images\\12.jpg",
            "E:\\eric2\\discord_bot_output\\images\\14.jpg",
            "E:\\eric2\\discord_bot_output\\images\\15.jpg",
            "E:\\eric2\\discord_bot_output\\images\\17.jpg",
            "E:\\eric2\\discord_bot_output\\images\\18.jpg",
            "E:\\eric2\\discord_bot_output\\images\\19.jpg",
            "E:\\eric2\\discord_bot_output\\images\\22.jpg",
            "E:\\eric2\\discord_bot_output\\images\\41.jpg",
            "E:\\eric2\\discord_bot_output\\images\\42.jpg",
            "E:\\eric2\\discord_bot_output\\images\\55.jpg",
            "E:\\eric2\\discord_bot_output\\images\\61.jpg",
            "E:\\eric2\\discord_bot_output\\images\\68.png",
            "E:\\eric2\\discord_bot_output\\images\\69.png",
            "E:\\eric2\\discord_bot_output\\images\\70.png",
            "E:\\eric2\\discord_bot_output\\images\\71.png",
            "E:\\eric2\\discord_bot_output\\images\\72.png",
            "E:\\eric2\\discord_bot_output\\images\\73.png",
            "E:\\eric2\\discord_bot_output\\images\\74.jpg",
            "E:\\eric2\\discord_bot_output\\images\\75.jpg",
            "E:\\eric2\\discord_bot_output\\images\\76.png",
            "E:\\eric2\\discord_bot_output\\images\\77.png",
            "E:\\eric2\\discord_bot_output\\images\\104.jpg",
            "E:\\eric2\\discord_bot_output\\images\\112.png",
            "E:\\eric2\\discord_bot_output\\images\\119.png",
            "E:\\eric2\\discord_bot_output\\images\\120.png",
            "E:\\eric2\\discord_bot_output\\images\\121.png",
            "E:\\eric2\\discord_bot_output\\images\\122.png",
            "E:\\eric2\\discord_bot_output\\images\\123.png",
            "E:\\eric2\\discord_bot_output\\images\\124.png",
            "E:\\eric2\\discord_bot_output\\images\\125.png",
            "E:\\eric2\\discord_bot_output\\images\\126.png",
            "E:\\eric2\\discord_bot_output\\images\\127.png",
            "E:\\eric2\\discord_bot_output\\images\\128.png",
            "E:\\eric2\\discord_bot_output\\images\\129.png",
            "E:\\eric2\\discord_bot_output\\images\\131.jpg",
            "E:\\eric2\\discord_bot_output\\images\\137.png",
            "E:\\eric2\\discord_bot_output\\images\\139.jpg",
            "E:\\eric2\\discord_bot_output\\images\\144.png",
            "E:\\eric2\\discord_bot_output\\images\\147.png",
            "E:\\eric2\\discord_bot_output\\images\\148.png",
            "E:\\eric2\\discord_bot_output\\images\\151.jpg",
            "E:\\eric2\\discord_bot_output\\images\\154.jpg",
            "E:\\eric2\\discord_bot_output\\images\\157.jpg",
            "E:\\eric2\\discord_bot_output\\images\\159.jpg",
            "E:\\eric2\\discord_bot_output\\images\\160.jpg",
            "E:\\eric2\\discord_bot_output\\images\\161.jpg",
            "E:\\eric2\\discord_bot_output\\images\\163.png",
            "E:\\eric2\\discord_bot_output\\images\\170.jpg",
            "E:\\eric2\\discord_bot_output\\images\\175.jpg",
            "E:\\eric2\\discord_bot_output\\images\\176.jpg",
            "E:\\eric2\\discord_bot_output\\images\\187.jpg",
            "E:\\eric2\\discord_bot_output\\images\\211.jpg",
            "E:\\eric2\\discord_bot_output\\images\\212.jpg",
            "E:\\eric2\\discord_bot_output\\images\\216.jpg",
            "E:\\eric2\\discord_bot_output\\images\\229.png",
            "E:\\eric2\\discord_bot_output\\images\\238.png",
            "E:\\eric2\\discord_bot_output\\images\\240.png",
            "E:\\eric2\\discord_bot_output\\images\\242.jpg",
            "E:\\eric2\\discord_bot_output\\images\\252.jpg",
            "E:\\eric2\\discord_bot_output\\images\\270.jpg",
            "E:\\eric2\\discord_bot_output\\images\\273.jpg",
            # 更多圖片...
        ],
        "responses": []
    },
    "炸": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\46.jpg",
            # 更多圖片...
        ],
        "responses": ["天天"]
    },
    "爛": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\1.jpg",
            "E:\\eric2\\discord_bot_output\\images\\4.jpg",
            "E:\\eric2\\discord_bot_output\\images\\7.jpg",
            "E:\\eric2\\discord_bot_output\\images\\8.jpg",
            "E:\\eric2\\discord_bot_output\\images\\10.jpg",
            "E:\\eric2\\discord_bot_output\\images\\11.jpg",
            "E:\\eric2\\discord_bot_output\\images\\12.jpg",
            "E:\\eric2\\discord_bot_output\\images\\14.jpg",
            "E:\\eric2\\discord_bot_output\\images\\15.jpg",
            "E:\\eric2\\discord_bot_output\\images\\17.jpg",
            "E:\\eric2\\discord_bot_output\\images\\18.jpg",
            "E:\\eric2\\discord_bot_output\\images\\19.jpg",
            "E:\\eric2\\discord_bot_output\\images\\22.jpg",
            "E:\\eric2\\discord_bot_output\\images\\41.jpg",
            "E:\\eric2\\discord_bot_output\\images\\42.jpg",
            "E:\\eric2\\discord_bot_output\\images\\55.jpg",
            "E:\\eric2\\discord_bot_output\\images\\61.jpg",
            "E:\\eric2\\discord_bot_output\\images\\68.png",
            "E:\\eric2\\discord_bot_output\\images\\69.png",
            "E:\\eric2\\discord_bot_output\\images\\70.png",
            "E:\\eric2\\discord_bot_output\\images\\71.png",
            "E:\\eric2\\discord_bot_output\\images\\72.png",
            "E:\\eric2\\discord_bot_output\\images\\73.png",
            "E:\\eric2\\discord_bot_output\\images\\74.jpg",
            "E:\\eric2\\discord_bot_output\\images\\75.jpg",
            "E:\\eric2\\discord_bot_output\\images\\76.png",
            "E:\\eric2\\discord_bot_output\\images\\77.png",
            "E:\\eric2\\discord_bot_output\\images\\104.jpg",
            "E:\\eric2\\discord_bot_output\\images\\105.jpg",
            "E:\\eric2\\discord_bot_output\\images\\106.jpg",
            "E:\\eric2\\discord_bot_output\\images\\112.png",
            "E:\\eric2\\discord_bot_output\\images\\119.png",
            "E:\\eric2\\discord_bot_output\\images\\120.png",
            "E:\\eric2\\discord_bot_output\\images\\121.png",
            "E:\\eric2\\discord_bot_output\\images\\122.png",
            "E:\\eric2\\discord_bot_output\\images\\123.png",
            "E:\\eric2\\discord_bot_output\\images\\124.png",
            "E:\\eric2\\discord_bot_output\\images\\125.png",
            "E:\\eric2\\discord_bot_output\\images\\126.png",
            "E:\\eric2\\discord_bot_output\\images\\127.png",
            "E:\\eric2\\discord_bot_output\\images\\128.png",
            "E:\\eric2\\discord_bot_output\\images\\129.png",
            "E:\\eric2\\discord_bot_output\\images\\131.jpg",
            "E:\\eric2\\discord_bot_output\\images\\133.png",
            "E:\\eric2\\discord_bot_output\\images\\134.png",
            "E:\\eric2\\discord_bot_output\\images\\135.jpg",
            "E:\\eric2\\discord_bot_output\\images\\136.png",
            "E:\\eric2\\discord_bot_output\\images\\137.png",
            "E:\\eric2\\discord_bot_output\\images\\139.jpg",
            "E:\\eric2\\discord_bot_output\\images\\140.jpg",
            "E:\\eric2\\discord_bot_output\\images\\142.png",
            "E:\\eric2\\discord_bot_output\\images\\144.png",
            "E:\\eric2\\discord_bot_output\\images\\147.png",
            "E:\\eric2\\discord_bot_output\\images\\148.png",
            "E:\\eric2\\discord_bot_output\\images\\150.png",
            "E:\\eric2\\discord_bot_output\\images\\151.jpg",
            "E:\\eric2\\discord_bot_output\\images\\153.jpg",
            "E:\\eric2\\discord_bot_output\\images\\154.jpg",
            "E:\\eric2\\discord_bot_output\\images\\155.jpg",
            "E:\\eric2\\discord_bot_output\\images\\156.jpg",
            "E:\\eric2\\discord_bot_output\\images\\157.jpg",
            "E:\\eric2\\discord_bot_output\\images\\158.png",
            "E:\\eric2\\discord_bot_output\\images\\159.jpg",
            "E:\\eric2\\discord_bot_output\\images\\160.jpg",
            "E:\\eric2\\discord_bot_output\\images\\161.jpg",
            "E:\\eric2\\discord_bot_output\\images\\163.png",
            "E:\\eric2\\discord_bot_output\\images\\164.jpg",
            "E:\\eric2\\discord_bot_output\\images\\166.jpg",
            "E:\\eric2\\discord_bot_output\\images\\167.jpg",
            "E:\\eric2\\discord_bot_output\\images\\170.jpg",
            "E:\\eric2\\discord_bot_output\\images\\171.jpg",
            "E:\\eric2\\discord_bot_output\\images\\175.jpg",
            "E:\\eric2\\discord_bot_output\\images\\176.jpg",
            "E:\\eric2\\discord_bot_output\\images\\177.png",
            "E:\\eric2\\discord_bot_output\\images\\179.jpg",
            "E:\\eric2\\discord_bot_output\\images\\183.png",
            "E:\\eric2\\discord_bot_output\\images\\187.jpg",
            "E:\\eric2\\discord_bot_output\\images\\189.png",
            "E:\\eric2\\discord_bot_output\\images\\212.jpg",
            "E:\\eric2\\discord_bot_output\\images\\216.jpg",
            "E:\\eric2\\discord_bot_output\\images\\226.jpg",
            "E:\\eric2\\discord_bot_output\\images\\229.png",
            "E:\\eric2\\discord_bot_output\\images\\230.png",
            "E:\\eric2\\discord_bot_output\\images\\231.png",
            "E:\\eric2\\discord_bot_output\\images\\233.png",
            "E:\\eric2\\discord_bot_output\\images\\234.png",
            "E:\\eric2\\discord_bot_output\\images\\235.png",
            "E:\\eric2\\discord_bot_output\\images\\240.png",
            "E:\\eric2\\discord_bot_output\\images\\242.jpg",
            "E:\\eric2\\discord_bot_output\\images\\245.png",
            "E:\\eric2\\discord_bot_output\\images\\263.jpg",
            "E:\\eric2\\discord_bot_output\\images\\266.jpg",
            "E:\\eric2\\discord_bot_output\\images\\267.jpg",
            "E:\\eric2\\discord_bot_output\\images\\271.jpg",
            "E:\\eric2\\discord_bot_output\\images\\272.jpg",
            "E:\\eric2\\discord_bot_output\\images\\274.jpg",
            "E:\\eric2\\discord_bot_output\\images\\275.jpg",
            "E:\\eric2\\discord_bot_output\\images\\276.jpg",
            # 更多圖片...
        ],
        "responses": []  # 爛 只回覆圖片
    },
    "HDCU": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\280.png",
            "E:\\eric2\\discord_bot_output\\images\\281.jpg",
            # 更多圖片...
        ],
        "responses": ["健身", "狼師"]
    },
    "課金": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\3.jpg",
            "E:\\eric2\\discord_bot_output\\images\\215.png",
            "E:\\eric2\\discord_bot_output\\images\\223.jpg",
            "E:\\eric2\\discord_bot_output\\images\\225.jpg",
            "E:\\eric2\\discord_bot_output\\images\\259.jpg",
            "E:\\eric2\\discord_bot_output\\images\\265.jpg",
            # 更多圖片...
        ],
        "responses": []  # 課金 只回覆圖片
    },
    "我好了": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\6.jpg",
            "E:\\eric2\\discord_bot_output\\images\\20.jpg",
            "E:\\eric2\\discord_bot_output\\images\\23.jpg",
            "E:\\eric2\\discord_bot_output\\images\\25.jpg",
            "E:\\eric2\\discord_bot_output\\images\\26.jpg",
            "E:\\eric2\\discord_bot_output\\images\\27.jpg",
            "E:\\eric2\\discord_bot_output\\images\\28.jpg",
            "E:\\eric2\\discord_bot_output\\images\\39.jpg",
            "E:\\eric2\\discord_bot_output\\images\\75.jpg",
            "E:\\eric2\\discord_bot_output\\images\\76.png",
            "E:\\eric2\\discord_bot_output\\images\\78.jpg",
            "E:\\eric2\\discord_bot_output\\images\\79.png",
            "E:\\eric2\\discord_bot_output\\images\\80.png",
            "E:\\eric2\\discord_bot_output\\images\\81.png",
            "E:\\eric2\\discord_bot_output\\images\\82.png",
            "E:\\eric2\\discord_bot_output\\images\\83.png",
            "E:\\eric2\\discord_bot_output\\images\\84.jpg",
            "E:\\eric2\\discord_bot_output\\images\\85.png",
            "E:\\eric2\\discord_bot_output\\images\\109.png",
            "E:\\eric2\\discord_bot_output\\images\\111.jpg",
            "E:\\eric2\\discord_bot_output\\images\\112.png",
            "E:\\eric2\\discord_bot_output\\images\\119.png",
            "E:\\eric2\\discord_bot_output\\images\\120.png",
            "E:\\eric2\\discord_bot_output\\images\\122.png",
            "E:\\eric2\\discord_bot_output\\images\\123.png",
            "E:\\eric2\\discord_bot_output\\images\\124.png",
            "E:\\eric2\\discord_bot_output\\images\\130.png",
            "E:\\eric2\\discord_bot_output\\images\\132.png",
            "E:\\eric2\\discord_bot_output\\images\\142.png",
            "E:\\eric2\\discord_bot_output\\images\\149.png",
            "E:\\eric2\\discord_bot_output\\images\\153.jpg",
            "E:\\eric2\\discord_bot_output\\images\\155.jpg",
            "E:\\eric2\\discord_bot_output\\images\\160.jpg",
            "E:\\eric2\\discord_bot_output\\images\\161.jpg",
            "E:\\eric2\\discord_bot_output\\images\\165.jpg",
            "E:\\eric2\\discord_bot_output\\images\\169.jpg",
            "E:\\eric2\\discord_bot_output\\images\\172.jpg",
            "E:\\eric2\\discord_bot_output\\images\\174.jpg",
            "E:\\eric2\\discord_bot_output\\images\\175.jpg",
            "E:\\eric2\\discord_bot_output\\images\\176.jpg",
            "E:\\eric2\\discord_bot_output\\images\\182.png",
            "E:\\eric2\\discord_bot_output\\images\\184.jpg",
            "E:\\eric2\\discord_bot_output\\images\\186.png",
            "E:\\eric2\\discord_bot_output\\images\\188.png",
            "E:\\eric2\\discord_bot_output\\images\\189.png",
            "E:\\eric2\\discord_bot_output\\images\\193.png",
            "E:\\eric2\\discord_bot_output\\images\\194.jpg",
            "E:\\eric2\\discord_bot_output\\images\\196.png",
            "E:\\eric2\\discord_bot_output\\images\\197.png",
            "E:\\eric2\\discord_bot_output\\images\\212.jpg",
            "E:\\eric2\\discord_bot_output\\images\\217.png",
            "E:\\eric2\\discord_bot_output\\images\\220.jpg",
            "E:\\eric2\\discord_bot_output\\images\\221.jpg",
            "E:\\eric2\\discord_bot_output\\images\\222.png",
            "E:\\eric2\\discord_bot_output\\images\\224.png",
            "E:\\eric2\\discord_bot_output\\images\\230.png",
            "E:\\eric2\\discord_bot_output\\images\\238.png",
            "E:\\eric2\\discord_bot_output\\images\\244.png",
            "E:\\eric2\\discord_bot_output\\images\\257.png",
            "E:\\eric2\\discord_bot_output\\images\\262.png",
            "E:\\eric2\\discord_bot_output\\images\\274.jpg",
            "E:\\eric2\\discord_bot_output\\images\\275.jpg",
            "E:\\eric2\\discord_bot_output\\images\\278.jpg",
            # 更多圖片...
        ],
        "responses": []  # 我好了 只回覆圖片
    },
    "色": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\5.png",
            "E:\\eric2\\discord_bot_output\\images\\28.jpg",
            "E:\\eric2\\discord_bot_output\\images\\39.jpg",
            "E:\\eric2\\discord_bot_output\\images\\43.jpg",
            "E:\\eric2\\discord_bot_output\\images\\48.jpg",
            "E:\\eric2\\discord_bot_output\\images\\50.jpg",
            "E:\\eric2\\discord_bot_output\\images\\51.jpg",
            "E:\\eric2\\discord_bot_output\\images\\52.jpg",
            "E:\\eric2\\discord_bot_output\\images\\53.png",
            "E:\\eric2\\discord_bot_output\\images\\54.jpg",
            "E:\\eric2\\discord_bot_output\\images\\56.png",
            "E:\\eric2\\discord_bot_output\\images\\57.png",
            "E:\\eric2\\discord_bot_output\\images\\58.jpg",
            "E:\\eric2\\discord_bot_output\\images\\59.png",
            "E:\\eric2\\discord_bot_output\\images\\60.jpg",
            "E:\\eric2\\discord_bot_output\\images\\63.png",
            "E:\\eric2\\discord_bot_output\\images\\64.png",
            "E:\\eric2\\discord_bot_output\\images\\76.png",
            "E:\\eric2\\discord_bot_output\\images\\79.png",
            "E:\\eric2\\discord_bot_output\\images\\80.png",
            "E:\\eric2\\discord_bot_output\\images\\82.png",
            "E:\\eric2\\discord_bot_output\\images\\85.png",
            "E:\\eric2\\discord_bot_output\\images\\109.png",
            "E:\\eric2\\discord_bot_output\\images\\118.png",
            "E:\\eric2\\discord_bot_output\\images\\119.png",
            "E:\\eric2\\discord_bot_output\\images\\120.png",
            "E:\\eric2\\discord_bot_output\\images\\121.png",
            "E:\\eric2\\discord_bot_output\\images\\122.png",
            "E:\\eric2\\discord_bot_output\\images\\123.png",
            "E:\\eric2\\discord_bot_output\\images\\132.png",
            "E:\\eric2\\discord_bot_output\\images\\138.png",
            "E:\\eric2\\discord_bot_output\\images\\142.png",
            "E:\\eric2\\discord_bot_output\\images\\161.jpg",
            "E:\\eric2\\discord_bot_output\\images\\166.jpg",
            "E:\\eric2\\discord_bot_output\\images\\168.jpg",
            "E:\\eric2\\discord_bot_output\\images\\169.jpg",
            "E:\\eric2\\discord_bot_output\\images\\171.jpg",
            "E:\\eric2\\discord_bot_output\\images\\172.jpg",
            "E:\\eric2\\discord_bot_output\\images\\175.jpg",
            "E:\\eric2\\discord_bot_output\\images\\176.jpg",
            "E:\\eric2\\discord_bot_output\\images\\180.png",
            "E:\\eric2\\discord_bot_output\\images\\182.png",
            "E:\\eric2\\discord_bot_output\\images\\186.png",
            "E:\\eric2\\discord_bot_output\\images\\188.png",
            "E:\\eric2\\discord_bot_output\\images\\189.png",
            "E:\\eric2\\discord_bot_output\\images\\193.png",
            "E:\\eric2\\discord_bot_output\\images\\194.jpg",
            "E:\\eric2\\discord_bot_output\\images\\196.png",
            "E:\\eric2\\discord_bot_output\\images\\197.png",
            "E:\\eric2\\discord_bot_output\\images\\219.png",
            "E:\\eric2\\discord_bot_output\\images\\220.jpg",
            "E:\\eric2\\discord_bot_output\\images\\224.png",
            "E:\\eric2\\discord_bot_output\\images\\239.png",
            "E:\\eric2\\discord_bot_output\\images\\247.png",
            "E:\\eric2\\discord_bot_output\\images\\249.png",
            "E:\\eric2\\discord_bot_output\\images\\252.jpg",
            "E:\\eric2\\discord_bot_output\\images\\258.png",
            "E:\\eric2\\discord_bot_output\\images\\263.jpg",
            "E:\\eric2\\discord_bot_output\\images\\267.jpg",
            "E:\\eric2\\discord_bot_output\\images\\272.jpg",
            "E:\\eric2\\discord_bot_output\\images\\274.jpg",
            "E:\\eric2\\discord_bot_output\\images\\275.jpg",
            # 更多圖片...
        ],
        "responses": []  # 色 只回覆圖片
    },
    "奇怪的知識增加了": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\9.jpg",
            # 更多圖片...
        ],
        "responses": []  # 奇怪的知識增加了 只回覆圖片
    },
    "哭阿": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\13.gif",
            "E:\\eric2\\discord_bot_output\\images\\86.png",
            "E:\\eric2\\discord_bot_output\\images\\87.png",
            "E:\\eric2\\discord_bot_output\\images\\88.png",
            "E:\\eric2\\discord_bot_output\\images\\89.png",
            "E:\\eric2\\discord_bot_output\\images\\90.png",
            "E:\\eric2\\discord_bot_output\\images\\91.png",
            "E:\\eric2\\discord_bot_output\\images\\92.png",
            "E:\\eric2\\discord_bot_output\\images\\93.png",
            "E:\\eric2\\discord_bot_output\\images\\94.png",
            "E:\\eric2\\discord_bot_output\\images\\95.png",
            "E:\\eric2\\discord_bot_output\\images\\96.png",
            "E:\\eric2\\discord_bot_output\\images\\97.png",
            "E:\\eric2\\discord_bot_output\\images\\98.gif",
            "E:\\eric2\\discord_bot_output\\images\\99.jpg",
            "E:\\eric2\\discord_bot_output\\images\\148.png",
            "E:\\eric2\\discord_bot_output\\images\\185.png",
            "E:\\eric2\\discord_bot_output\\images\\190.png",
            "E:\\eric2\\discord_bot_output\\images\\216.jpg",
            "E:\\eric2\\discord_bot_output\\images\\226.jpg",
            "E:\\eric2\\discord_bot_output\\images\\233.png",
            "E:\\eric2\\discord_bot_output\\images\\234.png",
            # 更多圖片...
        ],
        "responses": []  # 哭阿 只回覆圖片
    },
    "哭啊": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\13.gif",
            "E:\\eric2\\discord_bot_output\\images\\86.png",
            "E:\\eric2\\discord_bot_output\\images\\87.png",
            "E:\\eric2\\discord_bot_output\\images\\88.png",
            "E:\\eric2\\discord_bot_output\\images\\89.png",
            "E:\\eric2\\discord_bot_output\\images\\90.png",
            "E:\\eric2\\discord_bot_output\\images\\91.png",
            "E:\\eric2\\discord_bot_output\\images\\92.png",
            "E:\\eric2\\discord_bot_output\\images\\93.png",
            "E:\\eric2\\discord_bot_output\\images\\94.png",
            "E:\\eric2\\discord_bot_output\\images\\95.png",
            "E:\\eric2\\discord_bot_output\\images\\96.png",
            "E:\\eric2\\discord_bot_output\\images\\97.png",
            "E:\\eric2\\discord_bot_output\\images\\98.gif",
            "E:\\eric2\\discord_bot_output\\images\\99.jpg",
            "E:\\eric2\\discord_bot_output\\images\\148.png",
            "E:\\eric2\\discord_bot_output\\images\\185.png",
            "E:\\eric2\\discord_bot_output\\images\\190.png",
            "E:\\eric2\\discord_bot_output\\images\\216.jpg",
            "E:\\eric2\\discord_bot_output\\images\\226.jpg",
            "E:\\eric2\\discord_bot_output\\images\\233.png",
            "E:\\eric2\\discord_bot_output\\images\\234.png",
            # 更多圖片...
        ],
        "responses": []  # 哭啊 只回覆圖片
    },
    "水餃": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\24.jpg",
            "E:\\eric2\\discord_bot_output\\images\\62.jpg",
            "E:\\eric2\\discord_bot_output\\images\\110.png",
            "E:\\eric2\\discord_bot_output\\images\\113.jpg",
            "E:\\eric2\\discord_bot_output\\images\\114.png",
            "E:\\eric2\\discord_bot_output\\images\\115.png",
            "E:\\eric2\\discord_bot_output\\images\\116.png",
            "E:\\eric2\\discord_bot_output\\images\\117.png",
            "E:\\eric2\\discord_bot_output\\images\\143.png",
            "E:\\eric2\\discord_bot_output\\images\\145.png",
            "E:\\eric2\\discord_bot_output\\images\\213.jpg",
            "E:\\eric2\\discord_bot_output\\images\\214.jpg",
            "E:\\eric2\\discord_bot_output\\images\\223.jpg",
            "E:\\eric2\\discord_bot_output\\images\\265.jpg",
            "E:\\eric2\\discord_bot_output\\images\\268.jpg",
            # 更多圖片...
        ],
        "responses": []  # 水餃 只回覆圖片
    },
    "睡覺": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\24.jpg",
            "E:\\eric2\\discord_bot_output\\images\\62.jpg",
            "E:\\eric2\\discord_bot_output\\images\\110.png",
            "E:\\eric2\\discord_bot_output\\images\\113.jpg",
            "E:\\eric2\\discord_bot_output\\images\\114.png",
            "E:\\eric2\\discord_bot_output\\images\\115.png",
            "E:\\eric2\\discord_bot_output\\images\\116.png",
            "E:\\eric2\\discord_bot_output\\images\\117.png",
            "E:\\eric2\\discord_bot_output\\images\\143.png",
            "E:\\eric2\\discord_bot_output\\images\\145.png",
            "E:\\eric2\\discord_bot_output\\images\\213.jpg",
            "E:\\eric2\\discord_bot_output\\images\\214.jpg",
            "E:\\eric2\\discord_bot_output\\images\\223.jpg",
            "E:\\eric2\\discord_bot_output\\images\\265.jpg",
            "E:\\eric2\\discord_bot_output\\images\\268.jpg",
            # 更多圖片...
        ],
        "responses": []  # 睡覺 只回覆圖片
    },
    "騙人": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\21.jpg",
            "E:\\eric2\\discord_bot_output\\images\\49.jpg",
            "E:\\eric2\\discord_bot_output\\images\\148.png",
            "E:\\eric2\\discord_bot_output\\images\\157.jpg",
            "E:\\eric2\\discord_bot_output\\images\\166.jpg",
            "E:\\eric2\\discord_bot_output\\images\\170.jpg",
            "E:\\eric2\\discord_bot_output\\images\\174.jpg",
            "E:\\eric2\\discord_bot_output\\images\\187.jpg",
            "E:\\eric2\\discord_bot_output\\images\\192.png",
            "E:\\eric2\\discord_bot_output\\images\\212.jpg",
            "E:\\eric2\\discord_bot_output\\images\\227.png",
            "E:\\eric2\\discord_bot_output\\images\\229.png",
            "E:\\eric2\\discord_bot_output\\images\\230.png",
            "E:\\eric2\\discord_bot_output\\images\\233.png",
            "E:\\eric2\\discord_bot_output\\images\\234.png",
            "E:\\eric2\\discord_bot_output\\images\\238.png",
            "E:\\eric2\\discord_bot_output\\images\\241.jpg",
            "E:\\eric2\\discord_bot_output\\images\\246.png",
            "E:\\eric2\\discord_bot_output\\images\\248.png",
            "E:\\eric2\\discord_bot_output\\images\\251.png",
            "E:\\eric2\\discord_bot_output\\images\\263.jpg",
            "E:\\eric2\\discord_bot_output\\images\\267.jpg",
            "E:\\eric2\\discord_bot_output\\images\\271.jpg",
            "E:\\eric2\\discord_bot_output\\images\\272.jpg",
            "E:\\eric2\\discord_bot_output\\images\\274.jpg",
            "E:\\eric2\\discord_bot_output\\images\\276.jpg",
            # 更多圖片...
        ],
        "responses": []  # 騙人 只回覆圖片
    },
    "陳政顯": {
        "responses": ["亂丟垃圾"] # 陳政顯 只回覆文字
    },
    "城鎮險": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\30.jpg",
            "E:\\eric2\\discord_bot_output\\images\\32.jpg",
            "E:\\eric2\\discord_bot_output\\images\\35.jpg",
            "E:\\eric2\\discord_bot_output\\images\\273.jpg",
            # 更多圖片...
        ],
        "responses": []  # 城鎮險 只回覆圖片
    },
    "周皓暐": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\26.jpg",
            "E:\\eric2\\discord_bot_output\\images\\27.jpg",
            "E:\\eric2\\discord_bot_output\\images\\33.jpg",
            "E:\\eric2\\discord_bot_output\\images\\273.jpg",
            "E:\\eric2\\discord_bot_output\\images\\280.png",
            "E:\\eric2\\discord_bot_output\\images\\281.jpg",
            # 更多圖片...
        ],
        "responses": []  # 周皓暐 只回覆圖片
    },
    "凡士林": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\28.jpg",
            "E:\\eric2\\discord_bot_output\\images\\29.jpg",
            "E:\\eric2\\discord_bot_output\\images\\34.png",
            "E:\\eric2\\discord_bot_output\\images\\36.png",
            "E:\\eric2\\discord_bot_output\\images\\37.jpg",
            "E:\\eric2\\discord_bot_output\\images\\38.jpg",
            "E:\\eric2\\discord_bot_output\\images\\39.jpg",
            "E:\\eric2\\discord_bot_output\\images\\40.jpg",
            "E:\\eric2\\discord_bot_output\\images\\41.jpg",
            "E:\\eric2\\discord_bot_output\\images\\42.jpg",
            "E:\\eric2\\discord_bot_output\\images\\43.jpg",
            "E:\\eric2\\discord_bot_output\\images\\44.jpg",
            "E:\\eric2\\discord_bot_output\\images\\45.jpg",
            "E:\\eric2\\discord_bot_output\\images\\47.jpg",
            "E:\\eric2\\discord_bot_output\\images\\146.png",
            "E:\\eric2\\discord_bot_output\\images\\273.jpg",
            # 更多圖片...
        ],
        "responses": []  # 凡士林 只回覆圖片
    },
    "ㄐㄐ": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\37.jpg",
            "E:\\eric2\\discord_bot_output\\images\\43.jpg",
            "E:\\eric2\\discord_bot_output\\images\\47.jpg",
            "E:\\eric2\\discord_bot_output\\images\\146.png",
            "E:\\eric2\\discord_bot_output\\images\\173.png",
            "E:\\eric2\\discord_bot_output\\images\\175.jpg",
            "E:\\eric2\\discord_bot_output\\images\\176.jpg",
            "E:\\eric2\\discord_bot_output\\images\\181.png",
            "E:\\eric2\\discord_bot_output\\images\\184.jpg",
            "E:\\eric2\\discord_bot_output\\images\\186.png",
            "E:\\eric2\\discord_bot_output\\images\\193.png",
            "E:\\eric2\\discord_bot_output\\images\\205.png",
            "E:\\eric2\\discord_bot_output\\images\\212.jpg",
            "E:\\eric2\\discord_bot_output\\images\\220.jpg",
            "E:\\eric2\\discord_bot_output\\images\\242.jpg",
            "E:\\eric2\\discord_bot_output\\images\\255.png",
            "E:\\eric2\\discord_bot_output\\images\\256.png",
            "E:\\eric2\\discord_bot_output\\images\\258.png",
            "E:\\eric2\\discord_bot_output\\images\\261.png",
            # 更多圖片...
        ],
        "responses": []  # ㄐㄐ 只回覆圖片
    },
    "香港腳": {
        "responses": ["""求求你們了別再貼疑似我香港腳的圖了
從我出道那一刻起
就已經成為眾多粉絲的生活重心
每當他們被生活壓得喘不過氣來的時候
只要看到我的蛋包飯魔法
就能找回活下去的希望
今天看到了那則貼文
雖然我知道貼文中是指我的可能性很少
畢竟動漫裡有那麽多紅髮樂團女
難免會有相似的存在
但是那個敘述真的太像了 我一看到就能反應過來
求求你們不要再討論這件事了
再這樣下去我的粉絲連唯一支持自己活下去的理由都沒有了"""]
    },
    "沒有路": {
        "responses": [
            "有時候我們可能會感到迷茫，但不要灰心。我們可以一起尋找新的道路或者尋求幫助。記住，每個人都會遇到挑戰，但我們可以找到解決辦法。",
            "當你覺得沒有路的時候，請記住，這可能只是一個短暫的階段。嘗試讓自己冷静下來，並嘗試新的觀點或方法。也許你會找到一個你從未想過的解決方案。",
            "有時候，當我們覺得沒有路可走的時候，其實是因為我們只專注於一個方向。試著轉變你的觀點，也許你會發現新的道路。",
            "沒有路的感覺往往源於困惑和不確定。這時候，最好的方法是尋求他人的建議，比如朋友、家人或專業人士。他們可能會給你提供新的視角和建議。",
            "當你感覺沒有路可走的時候，記住，生活中總會有轉彎的地方。有時，我們需要的只是一點時間和耐心，以便看到前方的新道路。",
            "感覺沒有路走是十分痛苦的。但請記住，我們都有能力去適應和克服困難。這可能需要時間，但你絕對有能力走出困境。",
            "當你覺得沒有路走，試著去接受這種感覺，而不是抗拒它。有時候，我們需要經歷這種痛苦的感覺，才能找到真正的解決方案。即使現在看不到出路，也請相信未來總會有解決的方法出現。",
            "當我們感覺沒有路的時候，這其實是一個很好的機會去反思我們的目標和價值觀。也許我們需要的不是找到出路，而是重新定義我們的目標和方向。"
        ]
    },
    "sb": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\66.jpg",
            "E:\\eric2\\discord_bot_output\\images\\67.jpg",
            "E:\\eric2\\discord_bot_output\\images\\68.png",
            "E:\\eric2\\discord_bot_output\\images\\73.png",
            "E:\\eric2\\discord_bot_output\\images\\75.jpg",
            "E:\\eric2\\discord_bot_output\\images\\77.png",
            "E:\\eric2\\discord_bot_output\\images\\100.jpg",
            "E:\\eric2\\discord_bot_output\\images\\101.jpg",
            "E:\\eric2\\discord_bot_output\\images\\102.jpg",
            "E:\\eric2\\discord_bot_output\\images\\103.jpg",
            "E:\\eric2\\discord_bot_output\\images\\104.jpg",
            "E:\\eric2\\discord_bot_output\\images\\105.jpg",
            "E:\\eric2\\discord_bot_output\\images\\106.jpg",
            "E:\\eric2\\discord_bot_output\\images\\107.jpg",
            "E:\\eric2\\discord_bot_output\\images\\137.png",
            "E:\\eric2\\discord_bot_output\\images\\139.jpg",
            "E:\\eric2\\discord_bot_output\\images\\142.png",
            "E:\\eric2\\discord_bot_output\\images\\144.png",
            "E:\\eric2\\discord_bot_output\\images\\147.png",
            "E:\\eric2\\discord_bot_output\\images\\148.png",
            "E:\\eric2\\discord_bot_output\\images\\151.jpg",
            "E:\\eric2\\discord_bot_output\\images\\153.jpg",
            "E:\\eric2\\discord_bot_output\\images\\154.jpg",
            "E:\\eric2\\discord_bot_output\\images\\157.jpg",
            "E:\\eric2\\discord_bot_output\\images\\159.jpg",
            "E:\\eric2\\discord_bot_output\\images\\160.jpg",
            "E:\\eric2\\discord_bot_output\\images\\161.jpg",
            "E:\\eric2\\discord_bot_output\\images\\163.png",
            "E:\\eric2\\discord_bot_output\\images\\164.jpg",
            "E:\\eric2\\discord_bot_output\\images\\166.jpg",
            "E:\\eric2\\discord_bot_output\\images\\170.jpg",
            "E:\\eric2\\discord_bot_output\\images\\171.jpg",
            "E:\\eric2\\discord_bot_output\\images\\175.jpg",
            "E:\\eric2\\discord_bot_output\\images\\176.jpg",
            "E:\\eric2\\discord_bot_output\\images\\184.jpg",
            "E:\\eric2\\discord_bot_output\\images\\189.png",
            "E:\\eric2\\discord_bot_output\\images\\211.jpg",
            "E:\\eric2\\discord_bot_output\\images\\212.jpg",
            "E:\\eric2\\discord_bot_output\\images\\217.png",
            "E:\\eric2\\discord_bot_output\\images\\220.jpg",
            "E:\\eric2\\discord_bot_output\\images\\225.jpg",
            "E:\\eric2\\discord_bot_output\\images\\226.jpg",
            "E:\\eric2\\discord_bot_output\\images\\227.png",
            "E:\\eric2\\discord_bot_output\\images\\229.png",
            "E:\\eric2\\discord_bot_output\\images\\230.png",
            "E:\\eric2\\discord_bot_output\\images\\234.png",
            "E:\\eric2\\discord_bot_output\\images\\235.png",
            "E:\\eric2\\discord_bot_output\\images\\238.png",
            "E:\\eric2\\discord_bot_output\\images\\240.png",
            "E:\\eric2\\discord_bot_output\\images\\242.jpg",
            "E:\\eric2\\discord_bot_output\\images\\248.png",
            "E:\\eric2\\discord_bot_output\\images\\273.jpg",
            "E:\\eric2\\discord_bot_output\\images\\275.jpg",
            # 更多圖片...
        ],
        "responses": [
        "我們是否可以用更尊重的方式來交談？",
        "我覺得你的話語很冒犯，我不認為這種語言是適當的",
        "你為什麼要這樣說呢？"
        ]
    },
    "呀哈囉": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\65.png",
            # 更多圖片...
        ],
        "responses": []  # 呀哈囉 只回覆圖片
    },
    "ntr": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\108.png",
            "E:\\eric2\\discord_bot_output\\images\\141.jpg",
            "E:\\eric2\\discord_bot_output\\images\\162.jpg",
            "E:\\eric2\\discord_bot_output\\images\\166.jpg",
            "E:\\eric2\\discord_bot_output\\images\\169.jpg",
            "E:\\eric2\\discord_bot_output\\images\\174.jpg",
            "E:\\eric2\\discord_bot_output\\images\\175.jpg",
            "E:\\eric2\\discord_bot_output\\images\\176.jpg",
            "E:\\eric2\\discord_bot_output\\images\\178.png",
            "E:\\eric2\\discord_bot_output\\images\\179.jpg",
            "E:\\eric2\\discord_bot_output\\images\\180.png",
            "E:\\eric2\\discord_bot_output\\images\\182.png",
            "E:\\eric2\\discord_bot_output\\images\\183.png",
            "E:\\eric2\\discord_bot_output\\images\\189.png",
            "E:\\eric2\\discord_bot_output\\images\\194.jpg",
            "E:\\eric2\\discord_bot_output\\images\\195.jpg",
            "E:\\eric2\\discord_bot_output\\images\\219.png",
            "E:\\eric2\\discord_bot_output\\images\\226.jpg",
            "E:\\eric2\\discord_bot_output\\images\\229.png",
            "E:\\eric2\\discord_bot_output\\images\\239.png",
            "E:\\eric2\\discord_bot_output\\images\\240.png",
            "E:\\eric2\\discord_bot_output\\images\\242.jpg",
            "E:\\eric2\\discord_bot_output\\images\\243.jpg",
            "E:\\eric2\\discord_bot_output\\images\\248.png",
            "E:\\eric2\\discord_bot_output\\images\\250.png",
            "E:\\eric2\\discord_bot_output\\images\\252.jpg",
            "E:\\eric2\\discord_bot_output\\images\\254.png",
            "E:\\eric2\\discord_bot_output\\images\\255.png",
            "E:\\eric2\\discord_bot_output\\images\\258.png",
            "E:\\eric2\\discord_bot_output\\images\\261.png",
            "E:\\eric2\\discord_bot_output\\images\\264.jpg",
            "E:\\eric2\\discord_bot_output\\images\\268.jpg",
            "E:\\eric2\\discord_bot_output\\images\\277.jpg",
            # 更多圖片...
        ],
        "responses": []  # ntr 只回覆圖片
    },
    "hso": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\6.jpg",
            "E:\\eric2\\discord_bot_output\\images\\20.jpg",
            "E:\\eric2\\discord_bot_output\\images\\23.jpg",
            "E:\\eric2\\discord_bot_output\\images\\25.jpg",
            "E:\\eric2\\discord_bot_output\\images\\26.jpg",
            "E:\\eric2\\discord_bot_output\\images\\27.jpg",
            "E:\\eric2\\discord_bot_output\\images\\28.jpg",
            "E:\\eric2\\discord_bot_output\\images\\39.jpg",
            "E:\\eric2\\discord_bot_output\\images\\75.jpg",
            "E:\\eric2\\discord_bot_output\\images\\76.png",
            "E:\\eric2\\discord_bot_output\\images\\78.jpg",
            "E:\\eric2\\discord_bot_output\\images\\79.png",
            "E:\\eric2\\discord_bot_output\\images\\80.png",
            "E:\\eric2\\discord_bot_output\\images\\81.png",
            "E:\\eric2\\discord_bot_output\\images\\82.png",
            "E:\\eric2\\discord_bot_output\\images\\83.png",
            "E:\\eric2\\discord_bot_output\\images\\84.jpg",
            "E:\\eric2\\discord_bot_output\\images\\85.png",
            "E:\\eric2\\discord_bot_output\\images\\109.png",
            "E:\\eric2\\discord_bot_output\\images\\111.jpg",
            "E:\\eric2\\discord_bot_output\\images\\112.png",
            "E:\\eric2\\discord_bot_output\\images\\119.png",
            "E:\\eric2\\discord_bot_output\\images\\120.png",
            "E:\\eric2\\discord_bot_output\\images\\122.png",
            "E:\\eric2\\discord_bot_output\\images\\123.png",
            "E:\\eric2\\discord_bot_output\\images\\124.png",
            "E:\\eric2\\discord_bot_output\\images\\130.png",
            "E:\\eric2\\discord_bot_output\\images\\5.png",
            "E:\\eric2\\discord_bot_output\\images\\43.jpg",
            "E:\\eric2\\discord_bot_output\\images\\48.jpg",
            "E:\\eric2\\discord_bot_output\\images\\50.jpg",
            "E:\\eric2\\discord_bot_output\\images\\51.jpg",
            "E:\\eric2\\discord_bot_output\\images\\52.jpg",
            "E:\\eric2\\discord_bot_output\\images\\53.png",
            "E:\\eric2\\discord_bot_output\\images\\54.jpg",
            "E:\\eric2\\discord_bot_output\\images\\56.png",
            "E:\\eric2\\discord_bot_output\\images\\57.png",
            "E:\\eric2\\discord_bot_output\\images\\58.jpg",
            "E:\\eric2\\discord_bot_output\\images\\59.png",
            "E:\\eric2\\discord_bot_output\\images\\60.jpg",
            "E:\\eric2\\discord_bot_output\\images\\63.png",
            "E:\\eric2\\discord_bot_output\\images\\64.png",
            "E:\\eric2\\discord_bot_output\\images\\118.png",
            "E:\\eric2\\discord_bot_output\\images\\121.png",
            "E:\\eric2\\discord_bot_output\\images\\132.png",
            "E:\\eric2\\discord_bot_output\\images\\138.png",
            "E:\\eric2\\discord_bot_output\\images\\142.png",
            "E:\\eric2\\discord_bot_output\\images\\153.jpg",
            "E:\\eric2\\discord_bot_output\\images\\161.jpg",
            "E:\\eric2\\discord_bot_output\\images\\166.jpg",
            "E:\\eric2\\discord_bot_output\\images\\168.jpg",
            "E:\\eric2\\discord_bot_output\\images\\169.jpg",
            "E:\\eric2\\discord_bot_output\\images\\171.jpg",
            "E:\\eric2\\discord_bot_output\\images\\174.jpg",
            "E:\\eric2\\discord_bot_output\\images\\175.jpg",
            "E:\\eric2\\discord_bot_output\\images\\176.jpg",
            "E:\\eric2\\discord_bot_output\\images\\184.jpg",
            "E:\\eric2\\discord_bot_output\\images\\186.png",
            "E:\\eric2\\discord_bot_output\\images\\188.png",
            "E:\\eric2\\discord_bot_output\\images\\189.png",
            "E:\\eric2\\discord_bot_output\\images\\193.png",
            "E:\\eric2\\discord_bot_output\\images\\194.jpg",
            "E:\\eric2\\discord_bot_output\\images\\196.png",
            "E:\\eric2\\discord_bot_output\\images\\197.png",
            "E:\\eric2\\discord_bot_output\\images\\219.png",
            "E:\\eric2\\discord_bot_output\\images\\220.jpg",
            "E:\\eric2\\discord_bot_output\\images\\222.png",
            "E:\\eric2\\discord_bot_output\\images\\224.png",
            "E:\\eric2\\discord_bot_output\\images\\230.png",
            "E:\\eric2\\discord_bot_output\\images\\239.png",
            "E:\\eric2\\discord_bot_output\\images\\245.png",
            "E:\\eric2\\discord_bot_output\\images\\263.jpg",
            "E:\\eric2\\discord_bot_output\\images\\272.jpg",
            "E:\\eric2\\discord_bot_output\\images\\274.jpg",
            "E:\\eric2\\discord_bot_output\\images\\275.jpg",
            # 更多圖片...
        ],
        "responses": []  # hso 只回覆圖片
    },
    "幹你娘": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\48.jpg",
            "E:\\eric2\\discord_bot_output\\images\\51.jpg",
            "E:\\eric2\\discord_bot_output\\images\\52.jpg",
            "E:\\eric2\\discord_bot_output\\images\\53.png",
            "E:\\eric2\\discord_bot_output\\images\\54.jpg",
            "E:\\eric2\\discord_bot_output\\images\\56.png",
            "E:\\eric2\\discord_bot_output\\images\\58.jpg",
            "E:\\eric2\\discord_bot_output\\images\\59.png",
            "E:\\eric2\\discord_bot_output\\images\\66.jpg",
            "E:\\eric2\\discord_bot_output\\images\\71.png",
            "E:\\eric2\\discord_bot_output\\images\\72.png",
            "E:\\eric2\\discord_bot_output\\images\\73.png",
            "E:\\eric2\\discord_bot_output\\images\\75.jpg",
            "E:\\eric2\\discord_bot_output\\images\\76.png",
            "E:\\eric2\\discord_bot_output\\images\\77.png",
            "E:\\eric2\\discord_bot_output\\images\\78.jpg",
            "E:\\eric2\\discord_bot_output\\images\\79.png",
            "E:\\eric2\\discord_bot_output\\images\\80.png",
            "E:\\eric2\\discord_bot_output\\images\\82.png",
            "E:\\eric2\\discord_bot_output\\images\\104.jpg",
            "E:\\eric2\\discord_bot_output\\images\\107.jpg",
            "E:\\eric2\\discord_bot_output\\images\\109.png",
            "E:\\eric2\\discord_bot_output\\images\\112.png",
            "E:\\eric2\\discord_bot_output\\images\\119.png",
            "E:\\eric2\\discord_bot_output\\images\\120.png",
            "E:\\eric2\\discord_bot_output\\images\\121.png",
            "E:\\eric2\\discord_bot_output\\images\\122.png",
            "E:\\eric2\\discord_bot_output\\images\\123.png",
            "E:\\eric2\\discord_bot_output\\images\\124.png",
            "E:\\eric2\\discord_bot_output\\images\\125.png",
            "E:\\eric2\\discord_bot_output\\images\\126.png",
            "E:\\eric2\\discord_bot_output\\images\\127.png",
            "E:\\eric2\\discord_bot_output\\images\\128.png",
            "E:\\eric2\\discord_bot_output\\images\\129.png",
            "E:\\eric2\\discord_bot_output\\images\\131.jpg",
            "E:\\eric2\\discord_bot_output\\images\\132.png",
            "E:\\eric2\\discord_bot_output\\images\\137.png",
            "E:\\eric2\\discord_bot_output\\images\\139.jpg",
            "E:\\eric2\\discord_bot_output\\images\\144.png",
            "E:\\eric2\\discord_bot_output\\images\\147.png",
            "E:\\eric2\\discord_bot_output\\images\\148.png",
            "E:\\eric2\\discord_bot_output\\images\\151.jpg",
            "E:\\eric2\\discord_bot_output\\images\\152.jpg",
            "E:\\eric2\\discord_bot_output\\images\\153.jpg",
            "E:\\eric2\\discord_bot_output\\images\\154.jpg",
            "E:\\eric2\\discord_bot_output\\images\\155.jpg",
            "E:\\eric2\\discord_bot_output\\images\\157.jpg",
            "E:\\eric2\\discord_bot_output\\images\\159.jpg",
            "E:\\eric2\\discord_bot_output\\images\\160.jpg",
            "E:\\eric2\\discord_bot_output\\images\\161.jpg",
            "E:\\eric2\\discord_bot_output\\images\\163.png",
            "E:\\eric2\\discord_bot_output\\images\\166.jpg",
            "E:\\eric2\\discord_bot_output\\images\\169.jpg",
            "E:\\eric2\\discord_bot_output\\images\\170.jpg",
            "E:\\eric2\\discord_bot_output\\images\\172.jpg",
            "E:\\eric2\\discord_bot_output\\images\\174.jpg",
            "E:\\eric2\\discord_bot_output\\images\\175.jpg",
            "E:\\eric2\\discord_bot_output\\images\\176.jpg",
            "E:\\eric2\\discord_bot_output\\images\\178.png",
            "E:\\eric2\\discord_bot_output\\images\\179.jpg",
            "E:\\eric2\\discord_bot_output\\images\\184.jpg",
            "E:\\eric2\\discord_bot_output\\images\\189.png",
            "E:\\eric2\\discord_bot_output\\images\\191.png",
            "E:\\eric2\\discord_bot_output\\images\\193.png",
            "E:\\eric2\\discord_bot_output\\images\\210.png",
            "E:\\eric2\\discord_bot_output\\images\\211.jpg",
            "E:\\eric2\\discord_bot_output\\images\\212.jpg",
            "E:\\eric2\\discord_bot_output\\images\\215.png",
            "E:\\eric2\\discord_bot_output\\images\\216.jpg",
            "E:\\eric2\\discord_bot_output\\images\\218.png",
            "E:\\eric2\\discord_bot_output\\images\\225.jpg",
            "E:\\eric2\\discord_bot_output\\images\\226.jpg",
            "E:\\eric2\\discord_bot_output\\images\\229.png",
            "E:\\eric2\\discord_bot_output\\images\\232.png",
            "E:\\eric2\\discord_bot_output\\images\\236.png",
            "E:\\eric2\\discord_bot_output\\images\\237.png",
            "E:\\eric2\\discord_bot_output\\images\\238.png",
            "E:\\eric2\\discord_bot_output\\images\\240.png",
            "E:\\eric2\\discord_bot_output\\images\\242.jpg",
            "E:\\eric2\\discord_bot_output\\images\\243.jpg",
            "E:\\eric2\\discord_bot_output\\images\\247.png",
            "E:\\eric2\\discord_bot_output\\images\\248.png",
            "E:\\eric2\\discord_bot_output\\images\\248.png",
            "E:\\eric2\\discord_bot_output\\images\\254.png",
            "E:\\eric2\\discord_bot_output\\images\\258.png",
            "E:\\eric2\\discord_bot_output\\images\\268.jpg",
            # 更多圖片...
        ],
        "responses": []  # 幹你娘 只回覆圖片
    },
    "出來了": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\5.png",
            "E:\\eric2\\discord_bot_output\\images\\23.jpg",
            "E:\\eric2\\discord_bot_output\\images\\25.jpg",
            "E:\\eric2\\discord_bot_output\\images\\48.jpg",
            "E:\\eric2\\discord_bot_output\\images\\51.jpg",
            "E:\\eric2\\discord_bot_output\\images\\52.jpg",
            "E:\\eric2\\discord_bot_output\\images\\53.png",
            "E:\\eric2\\discord_bot_output\\images\\54.jpg",
            "E:\\eric2\\discord_bot_output\\images\\56.png",
            "E:\\eric2\\discord_bot_output\\images\\59.png",
            "E:\\eric2\\discord_bot_output\\images\\60.jpg",
            "E:\\eric2\\discord_bot_output\\images\\64.png",
            "E:\\eric2\\discord_bot_output\\images\\66.jpg",
            "E:\\eric2\\discord_bot_output\\images\\71.png",
            "E:\\eric2\\discord_bot_output\\images\\76.png",
            "E:\\eric2\\discord_bot_output\\images\\80.png",
            "E:\\eric2\\discord_bot_output\\images\\82.png",
            "E:\\eric2\\discord_bot_output\\images\\83.png",
            "E:\\eric2\\discord_bot_output\\images\\85.png",
            "E:\\eric2\\discord_bot_output\\images\\109.png",
            "E:\\eric2\\discord_bot_output\\images\\111.jpg",
            "E:\\eric2\\discord_bot_output\\images\\112.png",
            "E:\\eric2\\discord_bot_output\\images\\124.png",
            "E:\\eric2\\discord_bot_output\\images\\141.jpg",
            "E:\\eric2\\discord_bot_output\\images\\147.png",
            "E:\\eric2\\discord_bot_output\\images\\149.png",
            "E:\\eric2\\discord_bot_output\\images\\155.jpg",
            "E:\\eric2\\discord_bot_output\\images\\161.jpg",
            "E:\\eric2\\discord_bot_output\\images\\165.jpg",
            "E:\\eric2\\discord_bot_output\\images\\169.jpg",
            "E:\\eric2\\discord_bot_output\\images\\174.jpg",
            "E:\\eric2\\discord_bot_output\\images\\175.jpg",
            "E:\\eric2\\discord_bot_output\\images\\176.jpg",
            "E:\\eric2\\discord_bot_output\\images\\184.jpg",
            "E:\\eric2\\discord_bot_output\\images\\186.png",
            "E:\\eric2\\discord_bot_output\\images\\188.png",
            "E:\\eric2\\discord_bot_output\\images\\189.png",
            "E:\\eric2\\discord_bot_output\\images\\193.png",
            "E:\\eric2\\discord_bot_output\\images\\194.jpg",
            "E:\\eric2\\discord_bot_output\\images\\196.png",
            "E:\\eric2\\discord_bot_output\\images\\197.png",
            "E:\\eric2\\discord_bot_output\\images\\198.jpg",
            "E:\\eric2\\discord_bot_output\\images\\217.png",
            "E:\\eric2\\discord_bot_output\\images\\220.jpg",
            "E:\\eric2\\discord_bot_output\\images\\222.png",
            "E:\\eric2\\discord_bot_output\\images\\224.png",
            "E:\\eric2\\discord_bot_output\\images\\228.png",
            "E:\\eric2\\discord_bot_output\\images\\230.png",
            "E:\\eric2\\discord_bot_output\\images\\238.png",
            "E:\\eric2\\discord_bot_output\\images\\248.png",
            "E:\\eric2\\discord_bot_output\\images\\262.png",
            "E:\\eric2\\discord_bot_output\\images\\274.jpg",
            "E:\\eric2\\discord_bot_output\\images\\278.jpg",
            "E:\\eric2\\discord_bot_output\\images\\279.jpg",
            # 更多圖片...
        ],
        "responses": []  # 出來了 只回覆圖片
    },
    "道歉": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\199.png",
            "E:\\eric2\\discord_bot_output\\images\\200.png",
            "E:\\eric2\\discord_bot_output\\images\\201.png",
            "E:\\eric2\\discord_bot_output\\images\\202.png",
            "E:\\eric2\\discord_bot_output\\images\\203.png",
            "E:\\eric2\\discord_bot_output\\images\\204.png",
            "E:\\eric2\\discord_bot_output\\images\\211.jpg",
            "E:\\eric2\\discord_bot_output\\images\\226.jpg",
            "E:\\eric2\\discord_bot_output\\images\\227.png",
            "E:\\eric2\\discord_bot_output\\images\\229.png",
            "E:\\eric2\\discord_bot_output\\images\\233.png",
            "E:\\eric2\\discord_bot_output\\images\\235.png",
            "E:\\eric2\\discord_bot_output\\images\\241.jpg",
            "E:\\eric2\\discord_bot_output\\images\\248.png",
            "E:\\eric2\\discord_bot_output\\images\\253.jpg",
            "E:\\eric2\\discord_bot_output\\images\\265.jpg",
            "E:\\eric2\\discord_bot_output\\images\\266.jpg",
            "E:\\eric2\\discord_bot_output\\images\\267.jpg",
            "E:\\eric2\\discord_bot_output\\images\\268.jpg",
            "E:\\eric2\\discord_bot_output\\images\\274.jpg",
            "E:\\eric2\\discord_bot_output\\images\\276.jpg",
            # 更多圖片...
        ],
        "responses": []  # 道歉 只回覆圖片
    },
    "去死": {
        "images": [
            "E:\\eric2\\discord_bot_output\\images\\206.png",
            "E:\\eric2\\discord_bot_output\\images\\207.png",
            "E:\\eric2\\discord_bot_output\\images\\208.png",
            "E:\\eric2\\discord_bot_output\\images\\209.png",
            "E:\\eric2\\discord_bot_output\\images\\211.jpg",
            "E:\\eric2\\discord_bot_output\\images\\212.jpg",
            "E:\\eric2\\discord_bot_output\\images\\216.jpg",
            "E:\\eric2\\discord_bot_output\\images\\217.png",
            "E:\\eric2\\discord_bot_output\\images\\218.png",
            "E:\\eric2\\discord_bot_output\\images\\225.jpg",
            "E:\\eric2\\discord_bot_output\\images\\226.jpg",
            "E:\\eric2\\discord_bot_output\\images\\227.png",
            "E:\\eric2\\discord_bot_output\\images\\229.png",
            "E:\\eric2\\discord_bot_output\\images\\230.png",
            "E:\\eric2\\discord_bot_output\\images\\236.png",
            "E:\\eric2\\discord_bot_output\\images\\240.png",
            "E:\\eric2\\discord_bot_output\\images\\242.jpg",
            "E:\\eric2\\discord_bot_output\\images\\243.jpg",
            "E:\\eric2\\discord_bot_output\\images\\244.png",
            "E:\\eric2\\discord_bot_output\\images\\247.png",
            "E:\\eric2\\discord_bot_output\\images\\254.png",
            "E:\\eric2\\discord_bot_output\\images\\260.png",
            "E:\\eric2\\discord_bot_output\\images\\263.jpg",
            "E:\\eric2\\discord_bot_output\\images\\268.jpg",
            "E:\\eric2\\discord_bot_output\\images\\269.gif",
            "E:\\eric2\\discord_bot_output\\images\\273.jpg",
            # 更多圖片...
        ],
        "responses": []  # 去死 只回覆圖片
    },
    # 可以添加更多偵測詞和對應的回應
}

#---------------------------------------------------------------------------------------------------------------------

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
        async with session.get('https://saucenao.com/search.php', params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                return '搜圖錯誤(30秒4次only)'

async def send_embed_results(message, results):
    key_mapping = {
        'title': '標題',
        'part': '集數',
        'author_name': '作者名',
        'author_url': '作者連結',
        'pixiv_id': 'P站ID',
        'member_name': '會員名',
        'member_id': '會員ID',
        'source': '來源',
        'year': '年份',
        'est_time': '出現時間',
        'created_at': '創建時間',
        'tweet_id': '推文ID',
        'twitter_user_id': 'X ID',
        'twitter_user_handle': 'X名',
        'creator': '創作者',
        'material': '材料',
        'characters': '角色',
        'danbooru_id': 'Danbooru ID',
        'gelbooru_id': 'Gelbooru ID',
        'yandere_id': 'Yandere ID',
        'eng_name': '英文名',
        'jp_name': '日文名'
    }

    for result in results.get('results', []):
        embed = Embed(title="搜圖結果", color=0x1e90ff)
        header = result.get('header', {})
        data = result.get('data', {})

        embed.add_field(name="相似度", value=header.get('similarity', 'N/A') + '%', inline=True)

        if 'source' in data:
            embed.add_field(name="來源", value=data['source'], inline=False)
        if 'title' in data:
            embed.add_field(name="標題", value=data['title'], inline=False)    
        if 'part' in data:
            embed.add_field(name="集數", value=data['part'], inline=True)    

        if 'est_time' in data:
            embed.add_field(name="出現時間", value=data['est_time'], inline=True)
        if 'year' in data:
            embed.add_field(name="年份", value=data['year'], inline=True)

        if 'ext_urls' in data:
            embed.add_field(name="連結", value="\n".join(data['ext_urls']), inline=False)

        for key in key_mapping:
            if key in data and key not in ['title', 'source', 'year', 'est_time', 'part']:
                embed.add_field(name=key_mapping[key], value=data[key], inline=True)

        if 'thumbnail' in header:
            embed.set_thumbnail(url=header['thumbnail'])

        await message.channel.send(embed=embed)

#---------------------------------------------------------------------------------------------------------------------

@bot.event
async def on_ready():
    # 設置機器人的活動狀態
    activity = discord.Game(name="台灣車禍模擬器")  # 創建一個遊戲活動，名為“台灣車禍模擬器”
    await bot.change_presence(activity=activity)  # 更改 bot 的 Presence 以顯示這個活動

    # 同步斜線指令
    slash = await bot.tree.sync()
    print(f"目前登入身份 --> {bot.user}")
    print(f"載入 {len(slash)} 個斜線指令")

#---------------------------------------------------------------------------------------------------------------------

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('?圖') or message.content.startswith('？圖'):
        if message.attachments:
            for attachment in message.attachments:
                if any(attachment.filename.lower().endswith(ext) for ext in ['jpg', 'jpeg', 'png', 'gif']):
                    image_url = attachment.url
                    print(f'Image URL: {image_url}')
                    results = await search_image(image_url)
                    if isinstance(results, str):
                        await message.channel.send(results)
                    else:
                        await send_embed_results(message, results)
                    return
        await message.channel.send('圖呢?')

    elif message.content.startswith('?看') or message.content.startswith('？看'):
        content = message.content[2:].strip()  # 移除?看並去除前後空白
        if message.attachments:
            for attachment in message.attachments:
                if any(attachment.filename.lower().endswith(ext) for ext in ['jpg', 'jpeg', 'png', 'gif']):
                    image_url = attachment.url
                    response = GPT4o_image_response(image_url, message.author.id)
                    await message.channel.send(response)
                    return
        elif content.startswith('http'):
            # 處理圖像鏈接
            response = GPT4o_image_response(content, message.author.id)
            await message.channel.send(response)
        else:
            await message.channel.send('圖呢?')

    elif message.content.startswith('?n') or message.content.startswith('？n'):
        code = message.content[2:].strip()  # 移除?n並去除前後空白
        if code.isdigit() and (5 <= len(code) <= 6):  # 檢查是否為五位或六位數字
            url = f'https://nhentai.net/g/{code}/'
            await message.channel.send(url)
        else:
            await message.channel.send('無效神諭')

    elif message.content.startswith('?w') or message.content.startswith('？w'):
        code = message.content[2:].strip()  # 移除?w並去除前後空白
        if code.isdigit() and (5 <= len(code) <= 6):  # 檢查是否為五位或六位數字
            url = f'https://www.wnacg.com/photos-slist-aid-{code}.html'
            await message.channel.send(url)
        else:
            await message.channel.send('無效神諭')

    elif message.content.startswith('?jm') or message.content.startswith('？jm'):
        code = message.content[3:].strip()
        if code.isdigit() and (5 <= len(code) <= 6):
            url = f'https://jmcomic.me/album/{code}/'
            await message.channel.send(url)
        else:
            await message.channel.send('無效神諭')

    elif message.content.startswith('?p') or message.content.startswith('？p'):
        code = message.content[2:].strip()  # 移除?p並去除前後空白
        if code.isdigit() and (8 <= len(code) <= 9):  # 檢查是否為八位或九位數字
            url = f'https://www.pixiv.net/artworks/{code}'
            await message.channel.send(url)
        else:
            await message.channel.send('無效神諭')
    
    # 檢查訊息是否包含偵測詞（排除URL），且確保偵測詞單獨出現
    elif not re.search(r'http[s]?://', message.content):
        for key in reply_dict.keys():
            # 使用正則表達式進行大小寫不敏感的匹配，並考慮 "?" 和 "？"
            if re.fullmatch(re.escape(key).replace("\\?","[?？]"), message.content.strip(), re.IGNORECASE):
                await send_custom_reply(message, key)
                break

async def send_custom_reply(message, user_message):
    if user_message in reply_dict:
        data = reply_dict[user_message]
        image_paths = data.get("images", [])
        response_options = data.get("responses", [])

        # 如果沒有圖片，只回覆文字
        if not image_paths:
            if response_options:
                response_text = random.choice(response_options)
                await message.channel.send(response_text)
            return

        # 隨機選擇一個圖片路徑
        image_path = random.choice(image_paths)

        if user_message == "幹" and image_path.split('\\')[-1] == '1.jpg':
            # 幹 特殊處理
            response_text = """⠀ ⠀ ⠀ ⠀ ⠀ ⠀⠀⣀⣀
　　　　 　⡏      ⠸
　　　       ⠸         ⢸
　　　　  ⢸    ⠀   ⢸
　　 　 ⡤ ⠸⠀⠀     ⠧ ⣀
　　     ⠃  ⢸　       ⢸       ⠳ 
           ⠻⠀⠀⠀⠀⠀⠀               ⠹
⠀       ⢹⡀　　　　　          ⢿
　         ⠳⡄⠀　　　　      ⣸
""" 
            response_image = discord.File(image_path)
            await message.channel.send(response_text, file=response_image)
        else:
            # 隨機選擇回覆文本或圖片
            if response_options and random.choice([True, False]):
                response_text = random.choice(response_options)
                await message.channel.send(response_text)
            else:
                response_image = discord.File(image_path)
                await message.reply(file=response_image, mention_author=True)

bot.run(TOKEN)
