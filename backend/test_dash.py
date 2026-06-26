import os
import sys

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.core.security import create_access_token


def main():
    token = create_access_token(data={"sub": "jeshu0069@gmail.com"})
    import requests

    res = requests.get("http://localhost:8000/api/v1/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    print(res.json())


if __name__ == "__main__":
    main()
