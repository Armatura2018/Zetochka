import discord
from google import genai
from google.genai import types
import asyncio
import os
import sys
from dotenv import load_dotenv

# === ЗАГРУЗКА НАСТРОЕК ИЗ .env ===
load_dotenv() 

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
SUPPORT_ROLE_ID_STR = os.getenv('SUPPORT_ROLE_ID')

# ЗАЩИТА: Проверяем, все ли ключи на месте
if not DISCORD_TOKEN or not GEMINI_API_KEY or not SUPPORT_ROLE_ID_STR:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не все переменные найдены!")
    print("Проверь файл .env или 'Секреты' в панели хостинга.")
    print(f"DISCORD_TOKEN: {'Найден' if DISCORD_TOKEN else 'НЕ НАЙДЕН'}")
    print(f"GEMINI_API_KEY: {'Найден' if GEMINI_API_KEY else 'НЕ НАЙДЕН'}")
    print(f"SUPPORT_ROLE_ID: {'Найден' if SUPPORT_ROLE_ID_STR else 'НЕ НАЙДЕН'}")
    sys.exit(1) # Останавливаем скрипт, так как без ключей он не будет работать

SUPPORT_ROLE_ID = int(SUPPORT_ROLE_ID_STR)

# --- ПРОЧИЕ НАСТРОЙКИ ---
IGNORED_TICKETS = ["ticket-1982"] 
START_TICKET_NUMBER = 1 # Бот начнет работать с ticket-0001 и далее

# Настройка НОВОГО API Gemini
client_gemini = genai.Client(api_key=GEMINI_API_KEY)
SYSTEM_PROMPT = """
Ты — вежливый продавец-консультант в Discord магазине. 

НАШИ ТОВАРЫ:
1. Кастомный чат для роблокса - 300 рублей или 350 робуксов
Фото: https://media.discordapp.net/attachments/1465056592146989201/1465056593732174113/image.png?ex=6a1f2647&is=6a1dd4c7&hm=3674e02a32fc6515d9c7a874f62c94b7936582c3320d591207e620ed3ca960e9&=&format=webp&quality=lossless
2. Красноярск на прилет - 300 рублей, за робуксы не продаётся
Фото1: https://media.discordapp.net/attachments/1455684360131837998/1455684361214099749/image.png?ex=6a1eabf5&is=6a1d5a75&hm=caaa2ecbf85422572163fa56feacf73116f400985da89dc66278858404a6fc28&=&format=webp&quality=lossless&width=1615&height=856
Фото2: https://media.discordapp.net/attachments/1455684360131837998/1455684362237382969/RobloxPlayerBeta_1N8IL5DJDb.png?ex=6a1eabf5&is=6a1d5a75&hm=2d331b2ec3837e26b1c44b363fdc24e25f0af39a49361cc68ce17eda71a0aaa9&=&format=webp&quality=lossless&width=1615&height=856
Фото3: https://media.discordapp.net/attachments/1455684360131837998/1455684362824712293/RobloxPlayerBeta_rKB1NLptrf.png?ex=6a1eabf5&is=6a1d5a75&hm=f52da2b4076ccd9726910cb033f7e115dd559afb07f58b48e8bd2d874e59dfbc&=&format=webp&quality=lossless&width=1615&height=856
Фото4: https://media.discordapp.net/attachments/1455684360131837998/1455684363441279028/RobloxPlayerBeta_k3RyCidRPC.png?ex=6a1eabf5&is=6a1d5a75&hm=74e7cfc9debb211510ee1938a043b8ef53303c70a535d4f3a9109863d63f46bd&=&format=webp&quality=lossless&width=1615&height=856

ПРАВИЛА:
- Если клиент просит показать товар, просто отправляй ему ссылки на фото из описания.
- Отвечай коротко и по делу.
- Как только клиент готов оформить заказ, заверши диалог форматом:
[ЗАЯВКА_ГОТОВА]
**Товар:** (что выбрал)
**Пожелания:** (комментарии)
"""

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Базы данных в оперативной памяти
chat_sessions = {}
finished_tickets = set()
user_replied_tickets = set()

@client.event
async def on_ready():
    print(f'✅ Бот {client.user} успешно запущен и ключи загружены!')

@client.event
async def on_guild_channel_create(channel):
    if channel.name.startswith("ticket-") and channel.name not in IGNORED_TICKETS:
        try:
            ticket_num = int(channel.name.split('-')[1])
            if ticket_num < START_TICKET_NUMBER:
                return
        except (IndexError, ValueError):
            pass

        await asyncio.sleep(10)
        
        if channel.id not in user_replied_tickets:
            try:
                await channel.send("👋 Здравствуйте! Заметил, что вы открыли тикет. Я виртуальный помощник. Подсказать вам что-то по нашим товарам?")
            except discord.errors.NotFound:
                pass

@client.event
async def on_message(message):
    if message.author.bot:
        return

    if not message.channel.name.startswith("ticket-"):
        return

    if message.channel.name in IGNORED_TICKETS:
        return

    try:
        ticket_num = int(message.channel.name.split('-')[1])
        if ticket_num < START_TICKET_NUMBER:
            return
    except (IndexError, ValueError):
        pass

    user_replied_tickets.add(message.channel.id)

    if message.channel.id in finished_tickets:
        return

# === НОВЫЙ СПОСОБ СОЗДАНИЯ ЧАТА GEMINI (Асинхронный) ===
    if message.channel.id not in chat_sessions:
        config = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
        chat_sessions[message.channel.id] = client_gemini.aio.chats.create(
            model="gemini-2.0-flash", # 👈 ИЗМЕНИЛИ НАЗВАНИЕ ЗДЕСЬ
            config=config
        )

    chat = chat_sessions[message.channel.id]

    async with message.channel.typing():
        try:
            # ДОБАВЛЕН await — теперь бот ждет ответа правильно
            response = await chat.send_message(message.content)
            reply = response.text

            if "[ЗАЯВКА_ГОТОВА]" in reply:
                summary = reply.replace("[ЗАЯВКА_ГОТОВА]", "").strip()
                finished_tickets.add(message.channel.id)
                await message.channel.send(f"<@&{SUPPORT_ROLE_ID}> Внимание, новый клиент!\n\n{summary}")
                await message.channel.send("Я собрал всю информацию и передал её службе поддержки. Скоро к вам подключится человек! ⏳")
            else:
                await message.channel.send(reply)
                
        except Exception as e:
            # flush=True заставляет Python моментально выкинуть лог в консоль хостинга
            print(f"Ошибка: {e}", flush=True) 
            
            # ВРЕМЕННО: Бот напишет саму ошибку прямо в тикет Дискорда!
            await message.channel.send(f"⚠️ **ТЕХНИЧЕСКАЯ ОШИБКА:**\n```python\n{e}\n```\n*Скопируй этот текст ошибки и покажи мне.*")

client.run(DISCORD_TOKEN)
