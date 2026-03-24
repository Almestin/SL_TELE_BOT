import sys
import os
from openai import OpenAI
import httpx
import base64
from openai import AsyncOpenAI


class ChatGptService:
    client: OpenAI = None
    message_list: list = None

    def __init__(self, token):
        # token = "sk-proj-" + token[:3:-1] if token.startswith('gpt:') else token
        self.client = AsyncOpenAI(api_key=token)
             # http_client=httpx.Client(proxy="http://18.199.183.77:49232"),

        self.message_list = []




    def send_message_list(self) -> str:
        completion = self.client.chat.completions.create(
            model="gpt-5-mini",
            messages=self.message_list,
            max_completion_tokens=3000,
             # temperature=0.9
        )
        message = completion.choices[0].message
        self.message_list.append(message)
        return message.content

    def set_prompt(self, prompt_text: str) -> None:
        self.message_list.clear()
        self.message_list.append({"role": "system", "content": prompt_text})

    async def add_message(self, message_text: str) -> str:
        self.message_list.append({"role": "user", "content": message_text})
        return  self.send_message_list()

    async def send_question(self, prompt_text: str, message_text: str):


        self.set_prompt(prompt_text)
        return await self.add_message(message_text)

    async def send_photo(self, photo_file):
        """
        Приймає об'єкт фото від Telegram, конвертує в Base64
        та надсилає в OpenAI для аналізу.
        """
        # 1. Завантажуємо фото з серверів Telegram в пам'ять (байтовий масив)
        file_info = await photo_file.get_file()
        image_bytes = await file_info.download_as_bytearray()

        # 2. Кодуємо зображення в Base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # 3. Формуємо спеціальний запит для моделі з підтримкою Vision
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Що зображено на цьому фото? Дай короткий опис українською мовою."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]

        # 4. Надсилаємо запит до OpenAI
        response = await self.client.chat.completions.create(
            model="gpt-4o",  # Використовуємо актуальну модель з Vision
            messages=messages,
            max_tokens=500
        )

        return response.choices[0].message.content