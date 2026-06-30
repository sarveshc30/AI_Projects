import re

with open("metrics.txt", "r", encoding="utf-8") as f:
    text = f.read()

metrics = re.findall(r"^(.*?)\nUNIT:", text, flags=re.MULTILINE)

print(metrics)