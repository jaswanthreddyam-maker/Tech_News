import urllib.request
import urllib.error
try:
    print(urllib.request.urlopen('http://localhost:8000/api/v1/news?limit=1').read().decode())
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print(e.read().decode())
except Exception as e:
    print("Other error:", e)
