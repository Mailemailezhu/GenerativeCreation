from PIL import Image
im = Image.open('D:/GenerativeCreation/data/_ui_v6a.png')
im.crop((0, 60, 70, 200)).resize((280, 560), Image.NEAREST).save('D:/GenerativeCreation/data/_crop_rail2.png')
print('OK')