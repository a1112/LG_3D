from pathlib import Path
import difflib

text1 = Path(r"config1").read_text()
text2 = Path(r"config2").read_text()
text3 = Path(r"config3").read_text()

# 使用 difflib 比对文本差异
diff1_2 = difflib.ndiff(text1.splitlines(), text2.splitlines())
diff1_3 = difflib.ndiff(text1.splitlines(), text3.splitlines())
diff2_3 = difflib.ndiff(text2.splitlines(), text3.splitlines())

# 打印差异
print("Text1 vs Text2:")
print('\n'.join(diff1_2))
print("\nText1 vs Text3:")
print('\n'.join(diff1_3))
print("\nText2 vs Text3:")
print('\n'.join(diff2_3))