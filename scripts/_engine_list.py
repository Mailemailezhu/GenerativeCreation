import json, urllib.request
def names(node, key):
    d = json.load(urllib.request.urlopen('http://127.0.0.1:8188/object_info/' + node, timeout=30))
    req = d[node]['input']['required']
    return req[key][0]
print('UNET', names('UnetLoaderGGUF', 'unet_name'))
print('CLIP', names('DualCLIPLoader', 'clip_name1'))
print('VAE', names('VAELoader', 'vae_name'))
