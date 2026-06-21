import requests
s = requests.Session()
s.post('http://localhost:5000/login', data={'username':'admin','password':'changeme'})

# Check errors
print("1. CN quotes:")
r = s.get('http://localhost:5000/api/v1/markets/CN/quotes?symbol=600519')
print(r.status_code, r.text[:300] if r.text else '')

print("\n2. Global quote:")
r = s.get('http://localhost:5000/api/v1/global/quote?symbol=AAPL&market=US')
print(r.status_code, r.text[:300] if r.text else '')

print("\n3. Moments (POST):")
r = s.post('http://localhost:5000/api/v1/moments')
print(r.status_code, r.text[:300] if r.text else '')