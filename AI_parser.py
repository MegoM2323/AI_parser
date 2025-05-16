import requests
import json
import os
import glob
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
        
API_KEY = ""
API_URL = "https://api.deepseek.com/v1/chat/completions"
with open('General_Template.txt', 'r', encoding='utf-8') as f:
    TEMPLATE = f.read()

def get_html(url: str) -> str:
    """
    Получает HTML страницы с помощью Selenium

    Args:
        url (str): URL страницы для получения HTML

    Returns:
        str: HTML код страницы или None в случае ошибки
    """
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Запуск в фоновом режиме
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        
        # Ждем загрузки страницы (максимум 10 секунд)
        WebDriverWait(driver, 10).until(
            lambda driver: driver.execute_script('return document.readyState') == 'complete'
        )
        
        html = driver.page_source
        driver.quit()
        return html
        
    except Exception as e:
        print(f"Ошибка при получении HTML: {str(e)}")
        if 'driver' in locals():
            driver.quit()
        return None

def send_prompt(prompt: str) -> str:
    """
    Отправляет промпт в DeepSeek API и возвращает ответ
    """
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
        
    except Exception as e:
        print(f"Ошибка при отправке запроса: {str(e)}")
        return None

def download_file(url: str, filename: str):
    """
    Скачивает файл по URL и сохраняет его с указанным именем.
    Поддерживает изображения, PDF и DOCX файлы.
    
    Args:
        url (str): URL файла для скачивания
        filename (str): Имя файла для сохранения
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        with open(filename, 'wb') as f:
            f.write(response.content)
            
        # print(f"Файл успешно скачан и сохранен как {filename}")
        
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при скачивании файла: {str(e)}")
    except IOError as e:
        print(f"Ошибка при сохранении файла: {str(e)}")

def main():
    print("Введите URL:")
    url = input()
    base_link = "https://" + url.split("/")[2]
    prompt = TEMPLATE + f" для этого товара {url}"
    html = get_html(url)
    response = send_prompt(prompt)
    if response and html:
        if not os.path.exists('Results'):
            os.makedirs('Results')
            
        existing_files = glob.glob('Results/response_*')
        max_num = 0
        for file in existing_files:  
            try:
                num = int(file.split('_')[1].split('.')[0])
                max_num = max(max_num, num)
            except:
                continue
                
        # Создаем новый файл с номером на 1 больше
        new_num = max_num + 1
        
        foldername = f'Results/response_{new_num}'
        if not os.path.exists(foldername):
            os.makedirs(foldername)
        if not os.path.exists(f'{foldername}/images'):
            os.makedirs(f'{foldername}/images')
        if not os.path.exists(f'{foldername}/documents'):
            os.makedirs(f'{foldername}/documents')

        with open(f'{foldername}/response.txt', 'w', encoding='utf-8') as f:
            f.write(response)
        with open(f'{foldername}/response_short.txt', 'w', encoding='utf-8') as f:
            f.write(response.split('<-- ПОЛНОЕ ОПИСАНИЕ -->')[0][26:])
        with open(f'{foldername}/response_long.txt', 'w', encoding='utf-8') as f:
            f.write(response.split('<-- ПОЛНОЕ ОПИСАНИЕ -->  ')[1])
            
        # with open(f'{foldername}/response.html', 'w', encoding='utf-8') as f:
            # f.write(response[response.find('```html') + 8 : response.rfind('```') - 1])
        
        try:
            # Извлечение ссылок на изображения
            image_regex = r'https?://[^\s\"\'<>]+?\.(jpg|jpeg|png|gif|bmp|svg)|(?<=src=["\'])\/[^\s\"\'<>]+?\.(jpg|jpeg|png|gif|bmp|svg)'
            images = [match.group(0) for match in re.finditer(image_regex, html)]
            for img_url in images:
                img_name = os.path.basename(img_url) if img_url.startswith('http') else img_url; full_url = img_url if img_url.startswith('http') else f'{base_link}{img_url}'; download_file(full_url, f'{foldername}/images/{img_name.split("/")[-1]}')
        except Exception as e:
            print(f"Ошибка при скачивании изображений: {str(e)}")
        try:
            # Извлечение ссылок на документы
            document_regex = r'https?://[^\s\"\'<>]+?\.(pdf|doc|docx|xls|xlsx|txt|odt|rtf)|(?<=href=["\'])\/[^\s\"\'<>]+?\.(pdf|doc|docx|xls|xlsx|txt|odt|rtf)'
            documents = [match.group(0) for match in re.finditer(document_regex, html)]
            for doc_url in documents:
                doc_name = os.path.basename(doc_url) if doc_url.startswith('http') else doc_url
                download_file(doc_url if doc_url.startswith('http') else f'{base_link}{doc_url}', f'{foldername}/documents/{doc_name.split("/")[-1]}')
        except Exception as e:
            print(f"Ошибка при скачивании документов: {str(e)}")

    else:
        print("Ошибка при получении ответа от DeepSeek или получения HTML")

if __name__ == "__main__":
    main()
    