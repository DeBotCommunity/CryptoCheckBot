import asyncio
import contextlib
from concurrent.futures import ThreadPoolExecutor
import regex as re
from telethon import events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from userbot import client
import pytesseract
from PIL import Image
import io

info = {'category': 'tools', 'pattern': '.checks', 'description': 'Статус ловца чеков'}

class ChecksModule:
    def __init__(self):
        self.client = client

        self.channel_id = -1111111
        self.auto_withdraw = False
        self.withdraw_to = 'ваш_тег'
        self.auto_unfollow = True
        self.anti_captcha = True

        self.code_regex = re.compile(r"t\.me/(CryptoBot|send|tonRocketBot|wallet|xrocket|xJetSwapBot|torwalletbot)\?start=(CQ[A-Za-z0-9]{10}|C-[A-Za-z0-9]{10}|t_[A-Za-z0-9]{15}|mci_[A-Za-z0-9]{15}|c_[a-z0-9]{24}|[A-Za-z0-9]{10})", re.IGNORECASE)
        self.url_regex = re.compile(r"https:\/\/t\.me\/\+(\w{12,})")
        self.public_regex = re.compile(r"https:\/\/t\.me\/(\w{4,})")

        self.profit = ['Вы получили ', '✅ Вы получили: ', '💰 Вы получили ', 'Вы обналичили чек на сумму:']

        self.replace_chars = ''' @#&+()*"'…;,!№•—–·±<{>}†★‡„“”«»‚‘’‹›¡¿‽~`|√π÷×§∆\\°^%©®™✓₤$₼€₸₾₶฿₳₥₦₫₿¤₲₩₮¥₽₻₷₱₧£₨¢₠₣₢₺₵₡₹₴₯₰₪'''
        self.translation = str.maketrans('', '', self.replace_chars)

        self.executor = ThreadPoolExecutor(max_workers=5)

        self.crypto_black_list = [1622808649, 1559501630, 1985737506, 5014831088, 6014729293, 5794061503, 6314389409]
        self.checks = set()
        self.max_checks = 100
        self.channels = []
        self.captches = []
        self.checks_count = 0
        self.register_handlers()

    def register_handlers(self) -> None:
        """
        Registers various event handlers for the client.
        """
        self.client.add_event_handler(self.func_checks, events.NewMessage(outgoing=True, pattern=r'^\.checks$'))
        self.client.add_event_handler(self.handle_wallet, events.NewMessage(chats=[1985737506], pattern="⚠️ Вы не можете активировать этот чек, так как вы не являетесь подписчиком канала"))
        self.client.add_event_handler(self.handle_cryptobot, events.NewMessage(chats=[1559501630, 1622808649], pattern="Чтобы"))
        self.client.add_event_handler(self.handle_xrocket, events.NewMessage(chats=[5014831088], pattern="Для активации чека"))
        self.client.add_event_handler(self.handle_xjetswap, events.NewMessage(chats=[5794061503]))
        self.client.add_event_handler(self.handle_info, events.NewMessage(chats=self.crypto_black_list, func=self.filter))
        self.client.add_event_handler(self.handle_info, events.MessageEdited(chats=self.crypto_black_list, func=self.filter))
        self.client.add_event_handler(self.handle_grabber, events.MessageEdited(outgoing=False, chats=self.crypto_black_list, blacklist_chats=True))
        self.client.add_event_handler(self.handle_grabber, events.NewMessage(outgoing=False, chats=self.crypto_black_list, blacklist_chats=True))
        if self.anti_captcha:
            self.client.add_event_handler(self.handle_photo_message, events.NewMessage(chats=[1559501630], func=lambda e: e.photo))
        if self.auto_withdraw:
            self.withdraw()

    def ocr_tesseract(self, file: bytes, language='eng') -> str:
        """
        Perform OCR using Tesseract on the provided image file.
        """
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(self.executor, pytesseract.image_to_string, Image.open(io.BytesIO(file)), lang=language)

    async def func_checks(self, event) -> None:
        """
        An asynchronous function that performs checks on an event.
        """
        await event.edit(f"🟢 <b>FULL WORK</b>\n\n📋 <b>Успешно активировано:</b> <code>{self.checks_count}</code>", parse_mode='HTML')

    async def withdraw(self) -> None:
        """
        Asynchronously withdraws funds.
        """
        while True:
            await asyncio.sleep(86400)
            await self.client.send_message('CryptoBot', message='/wallet')
            await asyncio.sleep(0.1)
            messages = await self.client.get_messages('CryptoBot', limit=1)
            message = messages[0].message
            lines = message.split('\n\n')
            for line in lines:
                if ':' in line:
                    if 'Доступно' in line:
                        data = line.split('\n')[2].split('Доступно: ')[1].split(' (')[0].split(' ')
                    else:
                        data = line.split(': ')[1].split(' (')[0].split(' ')
                    curency, summ = data[1], data[0]
                    try:
                        if summ == '0':
                            continue
                        result = (await self.client.inline_query('send', f'{summ} {curency}'))[0]
                        if 'Создать чек' in result.title:
                            await result.click(self.withdraw_to)
                    except Exception:
                        pass

    async def handle_wallet(self, event) -> None:
        """
        Handle the wallet event.
        """
        code = None
        try:
            for row in event.message.reply_markup.rows:
                for button in row.buttons:
                    try:
                        check = self.code_regex.search(button.url)
                        if check:
                            code = check.group(2)
                        channel = self.url_regex.search(button.url)
                        public_channel = self.public_regex.search(button.url)
                        if channel:
                            await self.client(ImportChatInviteRequest(channel.group(1)))
                        if public_channel:
                            await self.client(JoinChannelRequest(public_channel.group(1)))
                    except Exception:
                        pass
        except AttributeError:
            pass
        if code not in self.checks:
            await self.client.send_message('wallet', message=f'/start {code}')
            self.checks.add(code)

    async def handle_cryptobot(self, event) -> None:
        """
        Asynchronously handles the cryptobot event.
        """
        try:
            for row in event.message.reply_markup.rows:
                for button in row.buttons:
                    try:
                        channel = self.url_regex.search(button.url)
                        if channel:
                            await self.client(ImportChatInviteRequest(channel.group(1)))
                    except Exception:
                        pass
        except AttributeError:
            pass
        await event.message.click(data=b'check-subscribe')

    async def handle_xrocket(self, event) -> None:
        """
        Asynchronously handles the 'xrocket' event.
        """
        try:
            for row in event.message.reply_markup.rows:
                for button in row.buttons:
                    try:
                        channel = self.url_regex.search(button.url)
                        public_channel = self.public_regex.search(button.url)
                        if channel:
                            await self.client(ImportChatInviteRequest(channel.group(1)))
                        if public_channel:
                            await self.client(JoinChannelRequest(public_channel.group(1)))
                    except Exception:
                        pass
        except AttributeError:
            pass
        await event.message.click(data=b'Check')

    async def handle_xjetswap(self, event) -> None:
        """
        Handles the 'xjetswap' event.
        """
        try:
            for row in event.message.reply_markup.rows:
                for button in row.buttons:
                    try:
                        if (button.data.decode()).startswith(('showCheque_', 'activateCheque_')):
                            await event.message.click(data=button.data)
                    except Exception:
                        pass
                    channel = self.url_regex.search(button.url)
                    public_channel = self.public_regex.search(button.url)
                    if channel:
                        await self.client(ImportChatInviteRequest(channel.group(1)))
                    if public_channel:
                        await self.client(JoinChannelRequest(public_channel.group(1)))
        except AttributeError:
            pass

    async def filter(self, event) -> bool:
        """
        Filter the event based on the presence of certain words in the message text.
        """
        return any(
            word in event.message.text and 'отзыв' not in event.message.text and 'пополнение' not in event.message.text
            for word in self.profit
        )

    async def handle_info(self, event) -> None:
        """
        Handles the "info" event.
        """
        me = await self.client.get_me()
        my_usr = me.username
        try:
            bot = (await self.client.get_entity(event.message.peer_id.user_id))
            if bot.usernames:
                username = bot.usernames[0]
            else:
                username = bot.username
        except AttributeError:
            username = bot.username
        summ = event.raw_text
        for i in self.profit:
            summ = summ.replace(i, '')

        self.checks_count += 1
        await self.client.send_message(self.channel_id,
                                       message=f'✅ <b>Активирован чек на сумму:</b> <code>{summ}</code>\n\n'
                                               f'<b>Инициатор:</b> @{my_usr}\n<b>Бот:</b> @{username}\n'
                                               f'<b>Всего чеков после запуска активировано:</b> <code>{self.checks_count}</code>\n',
                                       parse_mode='HTML')

    async def handle_grabber(self, event) -> None:
        """
        Asynchronously handles the grabber event.
        """
        message_text = event.message.text.translate(self.translation)
        if codes := self.code_regex.findall(message_text):
            for bot_name, code in codes:
                if code not in self.checks:
                    await self.client.send_message(bot_name, message=f'/start {code}')
                    self.checks.add(code)
                    if len(self.checks) > self.max_checks:
                        self.checks.pop()
        with contextlib.suppress(AttributeError):
            for row in event.message.reply_markup.rows:
                for button in row.buttons:
                    with contextlib.suppress(AttributeError):
                        matches = self.code_regex.findall(button.url)
                        for match in matches:
                            bot_name, code = match[0], match[1]
                            if code not in self.checks:
                                await self.client.send_message(bot_name, message=f'/start {code}')
                                self.checks.add(code)
                                if len(self.checks) > self.max_checks:
                                    self.checks.pop()

    async def handle_photo_message(self, event) -> None:
        """
        Handles a photo message event.
        """
        photo = await event.download_media(bytes)
        recognized_text = await self.ocr_tesseract(file=photo)
        if recognized_text and recognized_text not in self.captches:
            await self.client.send_message('CryptoBot', message=recognized_text)
            await asyncio.sleep(0.1)
            message = (await self.client.get_messages('CryptoBot', limit=1))[0].message
            if 'Incorrect answer.' in message or 'Неверный ответ.' in message:
                await self.client.send_message(
                    self.channel_id,
                    message='<b>❌ Не удалось разгадать капчу, решите ее сами.</b>',
                    parse_mode='HTML',
                )
                print('[!] Ошибка антикаптчи > Не удалось разгадать каптчу, решите ее сами.')
                self.captches.append(recognized_text)
        print(f'[$] Антикаптча подключена!')

checks = ChecksModule()
