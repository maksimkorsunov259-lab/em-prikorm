"""Create standard installation sizes from the untouched original PNG, with no crop."""
import base64,os
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
source='data:image/png;base64,'+base64.b64encode((root/'assets/icon-original.png').read_bytes()).decode()
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox'])
 page=browser.new_page()
 for size in [180,192,512]:
  result=page.evaluate('''async ({source,size})=>{const image=new Image();image.src=source;await image.decode();const canvas=document.createElement('canvas');canvas.width=canvas.height=size;const c=canvas.getContext('2d');c.imageSmoothingEnabled=true;c.imageSmoothingQuality='high';c.drawImage(image,0,0,size,size);return canvas.toDataURL('image/png').split(',')[1];}''',{'source':source,'size':size})
  (root/f'assets/icon-{size}.png').write_bytes(base64.b64decode(result))
 browser.close()
print('PNG installation icons: 180, 192, 512; original unchanged')
