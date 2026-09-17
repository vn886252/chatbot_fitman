import urllib.request, json

data = json.dumps({
    "model": "qwen-coder",
    "messages": [{"role": "user", "content": "Viet ham Python tinh_bmi(kg, cm) tra ve BMI va phan loai. Chi tra ve code, khong giai thich."}],
    "max_tokens": 300,
    "temperature": 0.1
}).encode()

req = urllib.request.Request(
    "http://127.0.0.1:8888/v1/chat/completions",
    data=data,
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-unsloth-f9c9f456bca0cf8793c9dfcee857115d"
    },
    method="POST"
)
resp = urllib.request.urlopen(req, timeout=120)
result = json.loads(resp.read().decode())
content = result["choices"][0]["message"]["content"]

with open("scratch/unsloth_output.txt", "w", encoding="utf-8") as f:
    f.write(content)
print("Done! Check scratch/unsloth_output.txt")
