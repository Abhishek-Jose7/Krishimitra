import requests

url = (
    "https://api.agmarknet.gov.in/v1/prices-and-arrivals"
    "/date-wise/specific-commodity"
)

params = {
    "year": 2024,
    "month": "01",
    "stateId": 17,
    "commodityId": 116,
    "includeCsv": "true"
}

headers = {
    "accept": "application/json, text/plain, */*",
    "origin": "https://www.agmarknet.gov.in",
    "referer": "https://www.agmarknet.gov.in/",
    "user-agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36",
}

r = requests.get(url, params=params, headers=headers, timeout=30)

print("Status:", r.status_code)
print("Content-Type:", r.headers.get("content-type"))
print("First 500 chars:\n", r.text[:500])

# Save raw response to file regardless of what it is
with open("raw_response.txt", "w", encoding="utf-8") as f:
    f.write(r.text)

print("\nFull response saved to raw_response.txt")