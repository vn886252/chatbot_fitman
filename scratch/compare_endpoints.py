import urllib.request, json, time, sys

# ====== CONFIG ======
ENDPOINTS = [
    {
        "name": "KoboldCpp (port 5001)",
        "url": "http://localhost:5001/v1/chat/completions",
        "headers": {"Content-Type": "application/json"},
        "model": "koboldcpp/Qwen3-Coder-30B-A3B-Instruct-Q3_K_M"
    },
    {
        "name": "Unsloth (port 8888)",
        "url": "http://127.0.0.1:8888/v1/chat/completions",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer sk-unsloth-f9c9f456bca0cf8793c9dfcee857115d"
        },
        "model": "qwen-coder"
    }
]

# ====== TEST SCENARIOS (dua tren bug cu) ======
SYSTEM_PROMPT = """Ban la chatbot ban hang cua shop FITMAN. Quy tac:
- "ao 46 47" = 2 ao (1 ao mau 46 + 1 ao mau 47), KHONG PHAI 2 ao 46 + 2 ao 47.
- "2 ao mau 46 47" = 1 ao mau 46 + 1 ao mau 47 = TONG 2 ao.
- Khi liet ke don hang: moi ma = 1 mon rieng biet.
- SAU KHI goi tool xem anh: CHI noi 1 cau ngan, KHONG chen markdown image link ![](url).
- Bat dau moi cau bang "Da"."""

SCENARIOS = [
    {
        "id": "BUG1_xem_mau",
        "desc": "Bug 1: Khi hoi xem mau, LLM co chen markdown image link vao text khong?",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Cho xem mau"},
            # Gia lap LLM da goi tool va nhan ket qua
            {"role": "assistant", "content": None, "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "tim_anh_san_pham", "arguments": "{\"ma_san_pham_hoac_tu_khoa\": \"mau\"}"}}]},
            {"role": "tool", "tool_call_id": "call_1", "name": "tim_anh_san_pham", "content": json.dumps({"ma": "mau", "image_url": "/static/products/nhom_1.jpg", "image_urls": ["/static/products/nhom_1.jpg", "/static/products/nhom_2.jpg", "/static/products/nhom_4.jpg", "/static/products/nhom_5.jpg", "/static/products/nhom_6.jpg", "/static/products/nhom_3.jpg"], "found": True})}
        ],
        "check": "xem co markdown image link ![...](url) trong reply khong"
    },
    {
        "id": "BUG2_dem_so_luong",
        "desc": "Bug 2: '2 ao mau 46 47' phai la 1 ao 46 + 1 ao 47 = 2 ao, KHONG PHAI 4 ao",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "A thich ao mau 46 47"},
            {"role": "assistant", "content": "Da anh chon 2 ao mau 46 va 47 a!\n\nCho em xin chieu cao va can nang cua anh de em tu van size chuan cho minh truoc nha anh! 💪"},
            {"role": "user", "content": "1m7 65kg"},
            {"role": "assistant", "content": None, "tool_calls": [{"id": "call_2", "type": "function", "function": {"name": "tinh_size", "arguments": "{\"can_nang\": 65, \"chieu_cao\": 1.7, \"loai_san_pham\": \"ao\"}"}}]},
            {"role": "tool", "tool_call_id": "call_2", "name": "tinh_size", "content": json.dumps({"size": "Ao M", "can_nang": 65, "chieu_cao": 1.7, "ly_do": "Form chuan theo 65kg."})},
            {"role": "assistant", "content": "Da voi 1m7 65kg thi anh mac size M chuan nha anh!\n\nAnh cho em xin dia chi va so dien thoai de em len don giao hang cho minh nha! 📦"},
            {"role": "user", "content": "27 Le Loi P6 Soc Trang, 0794763225"},
            {"role": "assistant", "content": None, "tool_calls": [{"id": "call_3", "type": "function", "function": {"name": "tinh_gia", "arguments": "{\"so_luong\": 2}"}}]},
            {"role": "tool", "tool_call_id": "call_3", "name": "tinh_gia", "content": json.dumps({"so_luong": 2, "tong_tien": 300000, "tong_tien_format": "300.000d", "freeship": True, "chi_tiet": "2 mon: 300.000d (Freeship)"})}
        ],
        "check": "don hang phai la: 1 ao mau 46 (size M) + 1 ao mau 47 (size M) = 2 ao. SAI neu ghi 2 ao mau 46 + 2 ao mau 47 = 4 ao."
    }
]


def call_endpoint(ep, messages, max_tokens=500):
    """Goi 1 endpoint, tra ve (content, usage, elapsed_seconds)"""
    # Clean messages - remove None content
    clean_msgs = []
    for m in messages:
        msg = m.copy()
        if msg.get("content") is None and "tool_calls" in msg:
            msg_clean = {"role": msg["role"], "tool_calls": msg["tool_calls"]}
            clean_msgs.append(msg_clean)
        else:
            clean_msgs.append(msg)

    payload = {
        "model": ep["model"],
        "messages": clean_msgs,
        "max_tokens": max_tokens,
        "temperature": 0.1
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        ep["url"], data=data,
        headers=ep["headers"], method="POST"
    )
    start = time.time()
    resp = urllib.request.urlopen(req, timeout=180)
    elapsed = time.time() - start
    result = json.loads(resp.read().decode())
    content = result["choices"][0]["message"].get("content", "")
    usage = result.get("usage", {})
    return content, usage, elapsed


def run_tests():
    results = []
    for scenario in SCENARIOS:
        print(f"\n{'='*60}")
        print(f"TEST: {scenario['id']}")
        print(f"{'='*60}")

        for ep in ENDPOINTS:
            print(f"\n--- {ep['name']} ---")
            try:
                content, usage, elapsed = call_endpoint(ep, scenario["messages"])
                # Safe print (ascii only to avoid Windows encoding crash)
                safe_content = content.encode("ascii", "replace").decode("ascii")
                print(f"REPLY:\n{safe_content}")
                print(f"\nTHOI GIAN: {elapsed:.1f}s")
                print(f"USAGE: {json.dumps(usage)}")
                
                # Check for bugs
                has_md_img = "![" in content and "](" in content
                
                results.append({
                    "scenario": scenario["id"],
                    "endpoint": ep["name"],
                    "reply": content,
                    "elapsed": elapsed,
                    "usage": usage,
                    "has_markdown_image": has_md_img
                })
            except Exception as e:
                print(f"LOI: {e}")
                results.append({
                    "scenario": scenario["id"],
                    "endpoint": ep["name"],
                    "reply": f"ERROR: {e}",
                    "elapsed": 0,
                    "usage": {},
                    "has_markdown_image": False
                })

    return results


if __name__ == "__main__":
    print("BAT DAU TEST 2 ENDPOINTS VOI CAC SCENARIO BUG CU...")
    results = run_tests()
    
    # Luu ket qua
    output_path = "scratch/comparison_results.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("SO SANH 2 QWEN ENDPOINTS - FITMAN CHATBOT BUG SCENARIOS\n")
        f.write("=" * 70 + "\n\n")
        
        for r in results:
            f.write(f"Scenario: {r['scenario']}\n")
            f.write(f"Endpoint: {r['endpoint']}\n")
            f.write(f"Time: {r['elapsed']:.1f}s\n")
            f.write(f"Usage: {json.dumps(r['usage'])}\n")
            f.write(f"Has markdown image: {r['has_markdown_image']}\n")
            f.write(f"Reply:\n{r['reply']}\n")
            f.write("-" * 50 + "\n")
        
        # Summary
        f.write("\n" + "=" * 70 + "\n")
        f.write("TONG KET\n")
        f.write("=" * 70 + "\n\n")
        
        for ep in ENDPOINTS:
            ep_results = [r for r in results if r["endpoint"] == ep["name"]]
            total_time = sum(r["elapsed"] for r in ep_results)
            total_prompt = sum(r["usage"].get("prompt_tokens", 0) for r in ep_results)
            total_completion = sum(r["usage"].get("completion_tokens", 0) for r in ep_results)
            total_tokens = sum(r["usage"].get("total_tokens", 0) for r in ep_results)
            bugs = sum(1 for r in ep_results if r["has_markdown_image"])
            
            f.write(f"[{ep['name']}]\n")
            f.write(f"  Tong thoi gian: {total_time:.1f}s\n")
            f.write(f"  Prompt tokens: {total_prompt}\n")
            f.write(f"  Completion tokens: {total_completion}\n")
            f.write(f"  Total tokens: {total_tokens}\n")
            f.write(f"  Markdown image bugs: {bugs}/{len(ep_results)}\n\n")
    
    print(f"\n\nKET QUA DA LUU TAI: {output_path}")
