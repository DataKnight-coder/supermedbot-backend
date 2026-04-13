import urllib.request, json
req = urllib.request.Request('http://127.0.0.1:8000/api/questions/generate', 
    data=json.dumps({"category":"emergency", "mode":"tutor", "count":1}).encode('utf-8'), 
    headers={'Content-Type': 'application/json'})
try:
    res = urllib.request.urlopen(req)
    print(res.read().decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
