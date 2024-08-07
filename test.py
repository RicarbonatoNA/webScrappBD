import json
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd

class WebScraper:
    def __init__(self, configFile):
        self.configFile = configFile
        self.driver = None
        self.loadConfig()
        self.setupDriver()

    def loadConfig(self):
        with open(self.configFile) as f:
            self.config = json.load(f)

    def setupDriver(self):
        options = Options()
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.126 Safari/537.36")
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

    def setHeadersAndCookies(self, headers, cookies):
        if headers:
            for header, value in headers.items():
                self.driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {'headers': {header: value}})
        if cookies:
            for cookie in cookies:
                self.driver.add_cookie(cookie)

    def findElements(self, by, value):
        try:
            if by == 'xpath':
                return self.driver.find_elements(By.XPATH, value)
            elif by == 'css_selector':
                return self.driver.find_elements(By.CSS_SELECTOR, value)
            elif by == 'id':
                return self.driver.find_elements(By.ID, value)
            elif by == 'name':
                return self.driver.find_elements(By.NAME, value)
            elif by == 'class_name':
                return self.driver.find_elements(By.CLASS_NAME, value)
            elif by == 'tag_name':
                return self.driver.find_elements(By.TAG_NAME, value)
            elif by == 'link_text':
                return self.driver.find_elements(By.LINK_TEXT, value)
            elif by == 'partial_link_text':
                return self.driver.find_elements(By.PARTIAL_LINK_TEXT, value)
            else:
                raise ValueError(f"Unknown locator method: {by}")
        except Exception as e:
            print(f"Error finding elements: {e}")
            return []

    def performActions(self, actions):
        for action in actions:
            try:
                action_type = action.get("action")
                by = action.get("by")
                value = action.get("value")

                if action_type == "input" and by and value:
                    elements = self.findElements(by, value)
                    if elements:
                        elements[0].clear()
                        elements[0].send_keys(action.get("input_value", ""))
                    else:
                        print(f"Element not found for 'input' action: {value}")
                elif action_type == "keyboard" and "key" in action:
                    key = getattr(Keys, action["key"].upper(), None)
                    if key:
                        webdriver.ActionChains(self.driver).send_keys(key).perform()
                    else:
                        print(f"Invalid key: {action['key']}")
                elif action_type == "click" and by and value:
                    elements = self.findElements(by, value)
                    if elements:
                        elements[0].click()
                    else:
                        print(f"Element not found for 'click' action: {value}")
                elif action_type == "find_elements" and by and value:
                    foundElements = self.findElements(by, value)
                    data = {}
                    for column in action.get("columns", []):
                        header = column.get("header")
                        selector_pattern = column.get("selector_pattern")
                        data[header] = [element.find_element(By.CSS_SELECTOR, selector_pattern).text if element.find_element(By.CSS_SELECTOR, selector_pattern).text else None for element in foundElements]
                    print(f"Data found for 'find_elements': {data}")
                else:
                    print(f"Unrecognized action or missing data: {action_type}")

                sleep(action.get("wait", 1))  # Wait between actions
            except KeyError as e:
                print(f"Missing key in action: {e}")
            except Exception as e:
                print(f"Error performing action: {e}")

    def scrapePage(self, url, elements, headers=None, cookies=None, actions=None):
        self.driver.get(url)
        print(f"Page loaded: {url}")

        # Set headers and cookies
        self.setHeadersAndCookies(headers, cookies)

        wait = WebDriverWait(self.driver, 20)

        if actions:
            self.performActions(actions)

        data = {}
        if elements:
            try:
                for elementName, selector in elements.items():
                    try:
                        if 'wait_condition' in selector:
                            wait_condition = getattr(EC, selector['wait_condition'])((By.XPATH, selector['value']))
                            wait.until(wait_condition)
                        foundElements = self.findElements(selector['by'], selector['value'])
                        data[elementName] = [element.text if element.text else None for element in foundElements]
                        print(f"Element '{elementName}': {data[elementName]}")
                    except Exception as e:
                        print(f"Could not find element '{elementName}' on the page: {str(e)}")
                        data[elementName] = []  # Save an empty list if the element is not found
            except Exception as e:
                print(f"Error processing page '{url}': {str(e)}")

        return data

    def saveData(self, data, url, outputFilename=None):
        # Verifica si las listas en data tienen la misma longitud
        lengths = {key: len(value) for key, value in data.items()}
        max_length = max(lengths.values(), default=0)

        # Ajusta todas las listas para que tengan la misma longitud
        for key in data:
            if len(data[key]) < max_length:
                data[key].extend([None] * (max_length - len(data[key])))

        # Convierte data a DataFrame y guarda en un archivo Excel si los datos son válidos
        if all(len(value) > 0 for value in data.values()):
            df = pd.DataFrame(data)
            if not outputFilename:
                outputFilename = f"{url.split('//')[1].split('/')[0]}_scraped_data.xlsx"
            df.to_excel(outputFilename, index=False)
            print(f"Data from '{url}' saved to '{outputFilename}'")
        else:
            print(f"Could not save data from '{url}' due to missing data.")

    def run(self):
        for page in self.config['pages']:
            url = page.get('url', page.get('start_url'))
            elements = page.get('elements', None)
            headers = page.get('headers', None)
            cookies = page.get('cookies', None)
            actions = page.get('actions', None)
            outputFilename = page.get('output', {}).get('filename', None)

            # Extract data from the page
            data = self.scrapePage(url, elements, headers, cookies, actions)

            # Save extracted data
            self.saveData(data, url, outputFilename)

    def close(self):
        if self.driver:
            self.driver.quit()

if __name__ == "__main__":
    scraper = WebScraper('test.json')
    scraper.run()
    scraper.close()
