import re

def chuan_hoa_ma_quan(text: str) -> str:
    """
    Chuẩn hóa các mã quần dính liền (như 'quần 124', 'q124', 'quan 12', 'quần 134', 'quần 24', 'quần 1234')
    thành dạng danh sách mã riêng biệt (như 'quần 1, 2, 4').
    Quần short của Fitman chỉ có các mã đơn lẻ: 1, 2, 3, 4, 6, 7.
    """
    if not text:
        return text

    pattern = re.compile(
        r'(?i)\b(quần|quan|q|short|đùi)\s*([123467]{2,4})\b'
    )

    def replace_match(m):
        prefix = m.group(1)
        digits = m.group(2)
        clean_prefix = "quần" if prefix.lower() in ("q", "quần", "quan") else prefix
        formatted_numbers = ", ".join(digits)
        return f"{clean_prefix} {formatted_numbers}"

    return pattern.sub(replace_match, text)

tests = [
    ("lấy tôi áo 30 31 quần 124 đi shop", "lấy tôi áo 30 31 quần 1, 2, 4 đi shop"),
    ("quần 12", "quần 1, 2"),
    ("quần 134", "quần 1, 3, 4"),
    ("quần 24", "quần 2, 4"),
    ("quần 1234", "quần 1, 2, 3, 4"),
    ("q124", "quần 1, 2, 4"),
    ("Q124", "quần 1, 2, 4"),
    ("quan 12", "quần 1, 2"),
    ("quần 1", "quần 1"),
    ("quần 4", "quần 4"),
    ("0794763225", "0794763225"),
    ("áo 30 31", "áo 30 31"),
    ("áo 46 47", "áo 46 47"),
    ("cao 1m70 nặng 70kg", "cao 1m70 nặng 70kg"),
    ("quần 1 2 4", "quần 1 2 4"),
    ("quần 1, 2, 4", "quần 1, 2, 4"),
]

all_ok = True
for inp, exp in tests:
    actual = chuan_hoa_ma_quan(inp)
    if actual != exp:
        print(f"FAIL: {repr(inp)} -> {repr(actual)} (expected: {repr(exp)})")
        all_ok = False

if all_ok:
    print("ALL TESTS PASSED SUCCESSFULLY!")
