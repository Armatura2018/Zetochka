import discord
import google.generativeai as genai
import asyncio

# === НАСТРОЙКИ ===
DISCORD_TOKEN = '2f322d597a84fefe430d55b7a75a9dd3228b30002469a574e29b8a7efa5f0d56'
GEMINI_API_KEY = 'AQ.Ab8RN6JxXSE33sEnogt3aV8WRTFrmNY33i_1JqeZ01lknPSgJg'
SUPPORT_ROLE_ID = 1511111151230914680

# --- НОВЫЕ НАСТРОЙКИ ---
# Бот будет игнорировать тикеты с этими названиями:
IGNORED_TICKETS = ["ticket-1982"] 

# Начиная с какого номера тикета бот должен работать (если 0 - работает во всех)
START_TICKET_NUMBER = 0

# Настройка API Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Инструкция для ИИ (Добавили ссылки на фото)
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

model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=SYSTEM_PROMPT)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

chat_sessions = {}
finished_tickets = set()

@client.event
async def on_ready():
    print(f'Бот {client.user} успешно запущен!')

# === НОВОЕ: Автоматическое приветствие ===
@client.event
async def on_guild_channel_create(channel):
    # Проверяем, что это тикет и он не в черном списке
    if channel.name.startswith("ticket-") and channel.name not in IGNORED_TICKETS:
        
        # Проверяем стартовый номер (если в названии есть число)
        try:
            ticket_num = int(channel.name.split('-')[1])
            if ticket_num < START_TICKET_NUMBER:
                return # Игнорируем старые тикеты
        except (IndexError, ValueError):
            pass # Если после "ticket-" не число, просто продолжаем

        # Ждем 2 секунды, чтобы Ticket Tool успел добавить пользователя в канал
        await asyncio.sleep(2)
        await channel.send("👋 Здравствуйте! Я виртуальный помощник. Рассказать вам про наши товары или показать фотографии?")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if not message.channel.name.startswith("ticket-"):
        return

    # === НОВОЕ: Игнорируем каналы из черного списка ===
    if message.channel.name in IGNORED_TICKETS:
        return

    # === НОВОЕ: Игнорируем тикеты до определенного номера ===
    try:
        ticket_num = int(message.channel.name.split('-')[1])
        if ticket_num < START_TICKET_NUMBER:
            return
    except (IndexError, ValueError):
        pass

    if message.channel.id in finished_tickets:
        return

    if message.channel.id not in chat_sessions:
        chat_sessions[message.channel.id] = model.start_chat(history=[])

    chat = chat_sessions[message.channel.id]

    async with message.channel.typing():
        try:
            response = chat.send_message(message.content)
            reply = response.text

            if "[ЗАЯВКА_ГОТОВА]" in reply:
                summary = reply.replace("[ЗАЯВКА_ГОТОВА]", "").strip()
                finished_tickets.add(message.channel.id)
                await message.channel.send(f"<@&{SUPPORT_ROLE_ID}> Внимание, новый клиент!\n\n{summary}")
                await message.channel.send("Я собрал всю информацию и передал её службе поддержки. Скоро к вам подключится человек! ⏳")
            else:
                await message.channel.send(reply)
                
        except Exception as e:
            print(f"Ошибка: {e}")
            await message.channel.send("Произошла ошибка связи. Повторите, пожалуйста.")

client.run(DISCORD_TOKEN)