import logging
import aiohttp
from config import go_api_token, APIFRAME_API_KEY, midjourney_webhook_url

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(filename)s:%(lineno)d #%(levelname)-8s '
           '[%(asctime)s] - %(name)s - %(message)s')

# Основной URL для работы с Midjourney
GOAPI_URL = "https://api.goapi.ai/mj/v2"

# Резервный URL для работы с Midjourney
APIFRAME_URL = "https://api.apiframe.pro"

# Заголовки для API GoAPI (используется для взаимодействия с MidJourney)
GOAPI_HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-API-KEY': go_api_token  # Токен для доступа к GoAPI
}

# Заголовки для Apiframe
APIFRAME_HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': APIFRAME_API_KEY
}

# Класс для работы с GoAPI (MidJourney)
class GoAPI:
    def __init__(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        await self.session.close()

    async def create_request(self, data, action, request_id):

        data["webhook_endpoint"] = midjourney_webhook_url + "/" + str(request_id)  # Указываем вебхук для ответа
        data["notify_progress"] = True
        url=f"{GOAPI_URL}/{action}"

        logger.info(f"Отправка запроса к GoAPI: URL={url}, Data={data}")

        try:
            async with self.session.post(url, json=data, headers=GOAPI_HEADERS) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"Ошибка GoAPI: {response.status} - {error_text}")
                    raise Exception(f"GoAPI Error: {response.status} - {error_text}")
                response_content = await response.json()
                logger.info(response_content)
                return response_content
        except Exception as e:
            logger.info(f"Ошибка при запросе к GoAPI: {e}")
            raise

    async def imagine(self, prompt, request_id):
        data = {
            "process_mode": "fast",
            "prompt": prompt,
        }
        return await self.create_request(data, "imagine", request_id)

    async def upscale(self, task_id, index, request_id):
        data = {
            "origin_task_id": task_id,
            "index": index
        }
        return await self.create_request(data, "upscale", request_id)

    async def variation(self, task_id, index, request_id):
        data = {
            "origin_task_id": task_id,
            "index": index
        }
        return await self.create_request(data, "variation", request_id)

    async def outpaint(self, task_id, zoom_ratio, request_id):
        data = {
            "origin_task_id": task_id,
            "zoom_ratio": zoom_ratio
        }
        return await self.create_request(data, "outpaint", request_id)


# Класс работы с резервным API - ApiFrame
class ApiFrame:
    def __init__(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        await self.session.close()

    # async def create_request(self, data, action, request_id):

    #     data["webhook_endpoint"] = midjourney_webhook_url + "/" + str(request_id)
    #     data["notify_progress"] = True
    #     url = f"{APIFRAME_URL}/{action}"

    #     logger.info(f'Data: {data}, Action: {action}, Request ID: {request_id}')
    #     logger.info(f'WebHook: {data["webhook_endpoint"]}, url: {url}')

    #     try:
    #         async with self.session.post(url, json=data, headers=APIFRAME_HEADERS) as response:
    #             if response.status != 200:
    #                 error_text = await response.text()
    #                 logger.error(f"Ошибка ApiFrame: {response.status} - {error_text}")
    #                 raise Exception(f"ApiFrame Error: {response.status} - {error_text}")
    #             response_content = await response.json()
    #             logger.info(f"Ответ ApiFrame: {response_content}")
    #             return response_content
    #     except Exception as e:
    #         logger.error(f"Ошибка при запросе к ApiFrame: {e}")
    #         raise

    async def create_request(self, data, action, request_id):
        # Используем фиксированный webhook_endpoint без request_id
        data["webhook_endpoint"] = f"{midjourney_webhook_url}/api/midjourney"
        data["notify_progress"] = True
        url = f"{APIFRAME_URL}/{action}"

        logger.info(f'Data: {data}, Action: {action}, Request ID: {request_id}')
        logger.info(f'WebHook: {data["webhook_endpoint"]}, URL: {url}')

        try:
            async with self.session.post(url, json=data, headers=APIFRAME_HEADERS) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ошибка ApiFrame: {response.status} - {error_text}")
                    raise Exception(f"ApiFrame Error: {response.status} - {error_text}")
                response_content = await response.json()
                logger.info(f"Ответ ApiFrame: {response_content}")
                
                # Сохраняем task_id в базе данных для сопоставления с action_id
                task_id = response_content.get('task_id')
                if task_id:
                    await db.update_action_with_task_id(request_id, task_id)
                
                return response_content
        except Exception as e:
            logger.error(f"Ошибка при запросе к ApiFrame: {e}")
            raise

    async def imagine(self, prompt, request_id):
        data = {
            "prompt": prompt,
        }
        return await self.create_request(data, "imagine", request_id)

    async def upscale(self, task_id, index, request_id):
        data = {
            "parent_task_id": task_id,
            "index": index
        }
        return await self.create_request(data, "upscale", request_id)

    async def variation(self, task_id, index, request_id):
        data = {
            "parent_task_id": task_id,
            "index": index
        }
        return await self.create_request(data, "variation", request_id)

    async def outpaint(self, task_id, zoom_ratio, request_id):
        data = {
            "parent_task_id": task_id,
            "zoom_ratio": zoom_ratio
        }
        return await self.create_request(data, "outpaint", request_id)


class MidJourneyAPI:
    def __init__(self, primary_api="goapi"):
        self.primary_api = primary_api  # "goapi" или "apiframe"
        self.apiframe = ApiFrame()
        self.goapi = GoAPI()

    def set_primary_api(self, api_type):
        if api_type not in ["goapi", "apiframe"]:
            raise ValueError("Неподдерживаемый тип API")
        self.primary_api = api_type

    async def close(self):
        await self.apiframe.close()

    async def create_request(self, data, action, request_id):

        logger.info(f'Data: {data}, Action: {action}, Request ID: {request_id}')

        if self.primary_api == "goapi":
            try:
                response = await self.goapi.create_request(data, action, request_id)
                return response
            except Exception as e:
                logger.error(f"GoAPI недоступен: {e}.")
                # self.set_primary_api("apiframe")
        if self.primary_api == "apiframe":
            try:
                response = await self.apiframe.create_request(data, action, request_id)
                return response
            except Exception as e:
                logger.error(f"ApiFrame недоступен: {e}.")
                # self.set_primary_api("goapi")
                # Попробуем снова GoAPI
                try:
                    response = await GoAPI.create_request(data, action, request_id)
                    return response
                except Exception as e:
                    logger.error(f"GoAPI тоже недоступен: {e}.")
                    return None

    async def imagine(self, prompt, request_id):
        action = "imagine"
        if self.primary_api == "goapi":
            data = {
                "process_mode": "fast",
                "prompt": prompt,
                # Другие поля, необходимые для GoAPI
            }
        else:
            data = {
                "prompt": prompt,
                # Другие поля, необходимые для ApiFrame
            }
        return await self.create_request(data, action, request_id)

    async def upscale(self, task_id, index, request_id):
        action = "upscale"
        if self.primary_api == "goapi":
            data = {
                "origin_task_id": task_id,
                "index": index
            }
        else:
            data = {
                "parent_task_id": task_id,
                "index": index
            }
        return await self.create_request(data, action, request_id)

    async def variation(self, task_id, index, request_id):
        action = "variation"
        if self.primary_api == "goapi":
            data = {
                "origin_task_id": task_id,
                "index": index
            }
        else:
            data = {
                "parent_task_id": task_id,
                "index": index
            }
        return await self.create_request(data, action, request_id)

    async def outpaint(self, task_id, zoom_ratio, request_id):
        action = "outpaint"
        if self.primary_api == "goapi":
            data = {
                "origin_task_id": task_id,
                "zoom_ratio": zoom_ratio
            }
        else:
            data = {
                "parent_task_id": task_id,
                "zoom_ratio": zoom_ratio
            }
        return await self.create_request(data, action, request_id)