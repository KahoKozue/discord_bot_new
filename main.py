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
                {"type": "text", "text": "盡可能詳細描述這張圖，有文字就寫出來，如果非中文就把它翻譯成繁體中文"},
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

# 偵測詞和對應回應，如果只回復文字的會有點問題，有時要重複多幾次或傳其他的再回去用才正常
reply_dict = {
    "幹": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\gan"],
        "responses": []
    },
    "炸": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\zha"],
        "responses": ["天天"]
    },
    "爛": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\lan"],
        "responses": []
    },
    "HDCU": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\hdcu"],
        "responses": ["健身", "狼師"]
    },
    "課金": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\kejin"],
        "responses": []
    },
    "我好了": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\wohaoliao"],
        "responses": []
    },
    "色": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\se"],
        "responses": []
    },
    "奇怪的知識增加了": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\qiguai"],
        "responses": []
    },
    "哭阿": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\kua"],
        "responses": []
    },
    "哭啊": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\kua"],
        "responses": []
    },
    "水餃": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\shuijiao"],
        "responses": []
    },
    "睡覺": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\shuijiao"],
        "responses": []
    },
    "騙人": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\pianren"],
        "responses": []
    },
    "陳政顯": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\chengzhenxian"],
        "responses": ["亂丟垃圾"]
    },
    "城鎮險": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\chengzhenxian"],
        "responses": ["亂丟垃圾"]
    },
    "周皓暐": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\zhouhaowei"],
        "responses": []
    },
    "凡士林": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\fanshilin"],
        "responses": []
    },
    "ㄐㄐ": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\jiji"],
        "responses": []
    },
    "香港腳": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\foot"],
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
        "directories": ["E:\\eric2\\discord_bot_output\\images\\noway"],
        "responses": ["有時候我們可能會感到迷茫，但不要灰心。我們可以一起尋找新的道路或者尋求幫助。記住，每個人都會遇到挑戰，但我們可以找到解決辦法。", "當你覺得沒有路的時候，請記住，這可能只是一個短暫的階段。嘗試讓自己冷静下來，並嘗試新的觀點或方法。也許你會找到一個你從未想過的解決方案。", "有時候，當我們覺得沒有路可走的時候，其實是因為我們只專注於一個方向。試著轉變你的觀點，也許你會發現新的道路。"]
    },
    "sb": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\sb"],
        "responses": [
        "我們是否可以用更尊重的方式來交談？",
        "我覺得你的話語很冒犯，我不認為這種語言是適當的",
        "你為什麼要這樣說呢？"
        ]
    },
    "呀哈囉": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\yahaluo"],
        "responses": []
    },
    "ntr": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\ntr"],
        "responses": []
    },
    "hso": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\hso"],
        "responses": []
    },
    "幹你娘": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\ganniniang"],
        "responses": []
    },
    "出來了": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\chulailiao"],
        "responses": []
    },
    "道歉": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\daoqian"],
        "responses": []
    },
    "去死": {
        "directories": ["E:\\eric2\\discord_bot_output\\images\\qusi"],
        "responses": []
    },
    # 可以添加更多偵測詞和對應的回應
}

def get_random_image_path(directories):
    all_images = []
    for directory in directories:
        if os.path.exists(directory):
            images = [os.path.join(directory, img) for img in os.listdir(directory) if img.lower().endswith(('jpg', 'jpeg', 'png', 'gif'))]
            all_images.extend(images)
    if all_images:
        return random.choice(all_images)
    return None

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
        'material': '作品',
        'characters': '角色',
        'danbooru_id': 'Danbooru ID',
        'gelbooru_id': 'Gelbooru ID',
        'yandere_id': 'Yandere ID',
        'eng_name': '英文名',
        'jp_name': '日文名'
    }

    if 'error' in results:
        await message.channel.send(results['error'])
        return

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
        directories = data.get("directories", [])
        response_options = data.get("responses", [])

        # 隨機選擇一個圖片路徑
        image_path = get_random_image_path(directories)

        if user_message == "幹" and image_path and image_path.split('\\')[-1] == '1.jpg':
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
            elif image_path:
                response_image = discord.File(image_path)
                await message.reply(file=response_image, mention_author=True)

bot.run(TOKEN)
