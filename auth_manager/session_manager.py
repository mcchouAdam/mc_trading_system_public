import requests
import redis
import time
import os
from config import Config

REDIS_TOKEN_EXPIRY = 600 
SESSION_REFRESH_INTERVAL = 540
LOGIN_RETRY_DELAY = 10

HEADER_API_KEY = "X-CAP-API-KEY"
HEADER_CST = "CST"
HEADER_SECURITY_TOKEN = "X-SECURITY-TOKEN"

REDIS_KEY_CST = "CAPITAL_CST"
REDIS_KEY_TOKEN = "CAPITAL_TOKEN"

class CapitalSessionManager:
    def __init__(self):
        self.base_url = Config.get("CAPITAL_REST_URL", "https://demo-api-capital.backend-capital.com") 
        self.api_key = Config.get("CAPITAL_API_KEY")
        self.identifier = Config.get("CAPITAL_LOGIN_ID")
        self.password = Config.get("CAPITAL_PASSWORD")
        
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_password = os.getenv('REDIS_PASSWORD')
        self.redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=0, password=redis_password, decode_responses=True)

    def login(self):
        """Execute login and obtain session tokens"""
        url = f"{self.base_url}/api/v1/session"
        headers = {
            HEADER_API_KEY: self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "identifier": self.identifier,
            "password": self.password,
            "encryptedPassword": False
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            cst = response.headers.get(HEADER_CST)
            x_security_token = response.headers.get(HEADER_SECURITY_TOKEN)

            if cst and x_security_token:
                print("Successfully logged in to Capital.com")
                self.save_to_redis(cst, x_security_token)
                return True
            return False

        except requests.exceptions.RequestException as e:
            print(f"Login failed: {e}")
            return False

    def save_to_redis(self, cst, token):
        """Share tokens with the C++ module via Redis"""
        self.redis_client.set(REDIS_KEY_CST, cst, ex=REDIS_TOKEN_EXPIRY)
        self.redis_client.set(REDIS_KEY_TOKEN, token, ex=REDIS_TOKEN_EXPIRY)
        print("Tokens updated in Redis.")

    def run_keeper(self):
        """Session monitoring, auto-refresh every 9 minutes (Official session expiry is 10 minutes)"""
        while True:
            success = self.login()
            if success:
                time.sleep(SESSION_REFRESH_INTERVAL) 
            else:
                print(f"Retry login in {LOGIN_RETRY_DELAY} seconds...")
                time.sleep(LOGIN_RETRY_DELAY)

if __name__ == "__main__":
    manager = CapitalSessionManager()
    manager.run_keeper()
