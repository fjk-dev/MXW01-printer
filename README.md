# MXW01 Bluetooth Printer
Десктопное приложение для печати на термопринтере MXW01 через Bluetooth.
## Возможности
- Поиск устройств MXW01
- Markdown-редактор
- Вставка изображений с ПК или по URL
- Генерация QR-кодов
- Предпросмотр
- Тёмная и светлая темы
## Установка из исходников
```bash
git clone https://github.com/fjk-dev/MXW01-Printer.git
```
```bash
cd MXW01-Printer
```
```bash
pip install -r requirements.txt
```
```bash
python main.py
```
## Сборка в EXE
```bash
python -m PyInstaller --onefile --windowed --icon=app.ico --hidden-import=bleak.backends.winrt --hidden-import=PIL._tkinter_finder main.py
```
## Лицензия
MIT
