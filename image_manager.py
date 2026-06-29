import urllib.request
from io import BytesIO
from PIL import Image, ImageOps
import numpy as np
import os

class ImageManager:
    @staticmethod
    def load_image(source):
        if source.startswith(('http://', 'https://')):
            with urllib.request.urlopen(source, timeout=10) as resp:
                data = resp.read()
            return Image.open(BytesIO(data))
        elif os.path.isfile(source):
            return Image.open(source)
        else:
            raise FileNotFoundError(f"Не найден файл или URL: {source}")

    @staticmethod
    def apply_brightness_contrast(img, brightness=0, contrast=1.0):
        img = ImageOps.grayscale(img)
        arr = np.array(img, dtype=np.float32)
        arr += brightness
        arr = 128 + (arr - 128) * contrast
        np.clip(arr, 0, 255, out=arr)
        return Image.fromarray(arr.astype(np.uint8), mode='L')

    @staticmethod
    def ordered_dither(img):
        bayer = np.array([[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]], dtype=np.float32)
        factor = 255.0 / 16.0
        arr = np.array(img, dtype=np.float32)
        h, w = arr.shape
        res = np.zeros_like(arr)
        for y in range(h):
            for x in range(w):
                res[y,x] = 0 if arr[y,x] < bayer[y%4][x%4]*factor else 255
        return Image.fromarray(res.astype(np.uint8), mode='L')

    @staticmethod
    def floyd_dither(img):
        arr = np.array(img, dtype=np.float32)
        h, w = arr.shape
        for y in range(h):
            for x in range(w):
                old = arr[y,x]
                new = 0.0 if old < 128 else 255.0
                arr[y,x] = new
                err = old - new
                if x+1 < w:
                    arr[y,x+1] = np.clip(arr[y,x+1] + err * 7/16, 0, 255)
                if y+1 < h:
                    if x-1 >= 0:
                        arr[y+1,x-1] = np.clip(arr[y+1,x-1] + err * 3/16, 0, 255)
                    arr[y+1,x] = np.clip(arr[y+1,x] + err * 5/16, 0, 255)
                    if x+1 < w:
                        arr[y+1,x+1] = np.clip(arr[y+1,x+1] + err * 1/16, 0, 255)
        return Image.fromarray(arr.astype(np.uint8), mode='L')

    @staticmethod
    def simple_binarize(img):
        arr = np.array(img, dtype=np.uint8)
        arr = np.where(arr < 128, 0, 255).astype(np.uint8)
        return Image.fromarray(arr, mode='L')

    @classmethod
    def process_image(cls, source, width=384, brightness=0, contrast=1.0,
                      dither='floyd', invert=False, debug_prefix=None):
        """
        Обработка изображения для принтера.
        :param invert: True – инвертировать цвета (чёрный ↔ белый)
        :param debug_prefix: если задано, сохраняет промежуточные PNG с этим префиксом
        """
        print("[ImageManager] Используется ОБНОВЛЁННАЯ версия (с явным invert)")  # отладка

        img = cls.load_image(source)
        w_percent = width / float(img.size[0])
        h_size = int(float(img.size[1]) * w_percent)
        img = img.resize((width, h_size), Image.Resampling.LANCZOS)
        if debug_prefix:
            img.save(f"{debug_prefix}_0_resized.png")

        gray = cls.apply_brightness_contrast(img, brightness, contrast)
        if debug_prefix:
            gray.save(f"{debug_prefix}_1_gray.png")

        # Автоконтраст для улучшения чёткости (оставляем, он полезен)
        gray = ImageOps.autocontrast(gray, cutoff=0)
        if debug_prefix:
            gray.save(f"{debug_prefix}_2_autocontrast.png")

        if dither == 'ordered':
            dithered = cls.ordered_dither(gray)
        elif dither == 'floyd':
            dithered = cls.floyd_dither(gray)
        else:
            dithered = cls.simple_binarize(gray)
        if debug_prefix:
            dithered.save(f"{debug_prefix}_3_dithered.png")

        # Преобразуем в 1-бит (0=чёрный, 1=белый)
        bw = dithered.convert('1')
        if debug_prefix:
            bw.save(f"{debug_prefix}_4_before_invert.png")

        # Принудительная инверсия, если нужно
        if invert:
            bw = ImageOps.invert(bw)
            print("[ImageManager] Выполнена инверсия (invert=True)")
            if debug_prefix:
                bw.save(f"{debug_prefix}_5_after_invert.png")
        else:
            print("[ImageManager] Инверсия НЕ выполнялась (invert=False)")

        return bw

    @staticmethod
    def to_printer_bytes(img: Image.Image):
        w, h = img.size
        if w != 384:
            raise ValueError("Ширина должна быть 384 пикселя")
        pixels = img.load()
        byte_width = w // 8
        result = bytearray()
        for y in range(h):
            row = bytearray(byte_width)
            for x in range(w):
                if pixels[x, y] == 0:  # чёрный
                    byte_idx = x // 8
                    bit = x % 8
                    row[byte_idx] |= (1 << bit)
            result.extend(row)
        return bytes(result)