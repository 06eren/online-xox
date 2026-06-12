import sys
from PIL import Image

png_path = r"C:\Users\karga\.gemini\antigravity\brain\16a54c5f-e56d-492e-972a-9a80b8b8ce8e\xox_icon_1781267409515.png"
ico_path = r"C:\Users\karga\OneDrive\Masaüstü\OnlineXoX\icon.ico"

img = Image.open(png_path)
img.save(ico_path, format='ICO', sizes=[(256, 256)])
print("Icon created successfully.")
