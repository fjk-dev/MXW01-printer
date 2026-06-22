from PIL import Image, ImageDraw, ImageFont
import qrcode
import re
import math
from image_manager import ImageManager

class Renderer:
    def __init__(self, font_size=20, line_spacing=1.5):
        self.font_size = font_size
        self.line_spacing = line_spacing
        self.qr_size = 3
        self.img_scale = 1.0
        self._init_fonts()

    def _init_fonts(self):
        # Дефолтные шрифты с кириллицей
        font_regular = None
        font_bold = None
        
        font_candidates = [
            "DejaVuSans.ttf",
            "Arial.ttf",
            "segoeui.ttf",
            "verdana.ttf",
            "tahoma.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        
        for font_name in font_candidates:
            try:
                if font_regular is None:
                    font_regular = ImageFont.truetype(font_name, self.font_size)
            except:
                continue
        
        if font_regular is None:
            font_regular = ImageFont.load_default()
        
        self.font_regular = font_regular
        self.font_bold = font_regular
        self.font_mono = font_regular

    def render_to_image(self, markdown_text, default_qr_size=3, default_img_scale=100):
        self.qr_size = default_qr_size
        self.img_scale = default_img_scale / 100.0
        lines = markdown_text.split('\n')
        width = 384
        current_y = 20
        
        for line in lines:
            current_y += self._process_line(line, current_y, draw=False)
        
        height = int(current_y + 20)
        img = Image.new('1', (width, height), 1)
        draw = ImageDraw.Draw(img)
        self.draw = draw
        self.last_y = 20
        self.box_start = None
        self.box_type = 'solid'
        
        for line in lines:
            self._process_line(line, self.last_y, draw=True)
        
        return img

    def _process_line(self, line, current_y, draw=False):
        clean = line.strip()
        if clean == '':
            return self.font_size

        img_match = re.match(r'^\[(IMG|QR):(.+?)\]$', clean)
        if img_match:
            tag_type = img_match.group(1)
            content = img_match.group(2)
            return self._draw_image(tag_type, content, current_y, draw)

        if clean in ('---', '===', '~~~'):
            if draw:
                self._draw_line(clean, current_y)
            return 15

        if '[BOX' in clean:
            self.box_start = current_y
            self.box_type = 'dots' if ':dots' in clean else 'solid'
            return 0
        if '[/BOX]' in clean:
            if draw and self.box_start is not None:
                self._draw_box(self.box_start, current_y, self.box_type)
                self.box_start = None
            return 10

        is_centered = '[C]' in clean
        is_mono = '[M]' in clean
        clean = clean.replace('[C]', '').replace('[M]', '').strip()

        if clean.startswith('# '):
            size_mult = 1.4
            is_bold = True
            text = clean[2:]
        elif clean.startswith('## '):
            size_mult = 1.2
            is_bold = True
            text = clean[3:]
        else:
            size_mult = 1.0
            is_bold = False
            text = clean

        bullet = None
        indent = 0
        if text.startswith('* '):
            bullet = '•'
            indent = 20
            text = text[2:]
        elif text.startswith('> '):
            bullet = '>'
            indent = 20
            text = text[2:]

        font = self.font_bold if is_bold else self.font_regular
        if is_mono:
            font = self.font_mono
        
        font_size_actual = int(self.font_size * size_mult)
        try:
            font = font.font_variant(size=font_size_actual)
        except:
            pass

        line_height = font_size_actual * self.line_spacing

        if draw:
            bbox = self.draw.textbbox((0,0), text, font=font)
            text_width = bbox[2] - bbox[0]
            if is_centered:
                x = (384 - text_width) / 2
            else:
                x = 10 + indent

            if bullet == '•':
                self.draw.text((x-15, current_y), '•', fill=0, font=font)
            elif bullet == '>':
                cx = x - 12
                tri = [(cx, current_y), (cx+8, current_y+font_size_actual/2), (cx, current_y+font_size_actual)]
                self.draw.polygon(tri, fill=0)
            self.draw.text((x, current_y), text, fill=0, font=font)

        return line_height

    def _draw_image(self, tag_type, content, current_y, draw):
        try:
            if tag_type == 'QR':
                parts = content.split('|')
                text = parts[0].strip()
                qr_size = int(parts[1].strip()) if len(parts) > 1 else self.qr_size
                qr_size = max(1, min(10, qr_size))
                
                qr = qrcode.QRCode(version=1, box_size=qr_size, border=2)
                qr.add_data(text)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white").convert('1')
                img = img.point(lambda x: 1 - x)
            else:
                parts = content.split('|')
                source = parts[0].strip()
                img_scale = int(parts[1].strip()) / 100.0 if len(parts) > 1 else self.img_scale
                
                img = ImageManager.process_image(source)
                new_w = int(img.width * img_scale)
                new_h = int(img.height * img_scale)
                img = img.resize((new_w, new_h), Image.Resampling.NEAREST)
        except Exception as e:
            print(f"Ошибка загрузки изображения: {e}")
            return 10

        w, h = img.size
        x = (384 - w) // 2
        y = int(current_y)
        if draw:
            self.draw.bitmap((x, y), img, fill=0)
        return h + 10

    def _draw_line(self, line_type, y):
        if line_type == '---':
            self.draw.line([(5, y+5), (379, y+5)], fill=0)
        elif line_type == '===':
            self.draw.line([(5, y+3), (379, y+3)], fill=0)
            self.draw.line([(5, y+7), (379, y+7)], fill=0)
        else:
            points = []
            for x in range(5, 380, 2):
                points.append((x, y+5 + math.sin(x/5)*3))
            self.draw.line(points, fill=0)

    def _draw_box(self, y1, y2, style):
        if style == 'dots':
            dash = 5
            for x in range(2, 381, dash*2):
                self.draw.line([(x, y1-5), (x+dash, y1-5)], fill=0)
                self.draw.line([(x, y2+5), (x+dash, y2+5)], fill=0)
        else:
            self.draw.rectangle([2, y1-5, 380, y2+5], outline=0)