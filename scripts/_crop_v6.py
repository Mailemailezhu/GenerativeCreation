import sys
from PIL import Image
im = Image.open('D:/GenerativeCreation/data/_ui_v6a.png')
im.crop((1060, 780, 1440, 900)).resize((760, 240), Image.NEAREST).save('D:/GenerativeCreation/data/_crop_bottom.png')
im.crop((0, 60, 90, 900)).resize((180, 1680), Image.NEAREST).save('D:/GenerativeCreation/data/_crop_rail.png')
print('OK')