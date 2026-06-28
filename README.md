# Quick Translator 🌐

[English](#english) | [Русский](#русский)

---

## English

[![Download](https://img.shields.io/badge/Download-Latest%20Release-green?style=for-the-badge&logo=github)](https://github.com/kosolapkeen/quicktranslator/releases)

**Quick Translator** is a lightweight, fast, and game-safe screen & text translator for Windows. It runs in the system tray and is specifically optimized to work seamlessly inside games (like Minecraft) and other applications.

### 🌟 Features
*   **`Ctrl + Q` — Translate & Replace (RU ↔ EN)**: Type a message in Russian or English, press `Ctrl + Q`, and it is instantly replaced with the translation.
    *   *Smart Selection*: If you select a specific word, only that word is translated. If nothing is selected, the entire input field is translated.
    *   *Note*: This hotkey strictly translates between Russian and English.
*   **`Ctrl + E` — Translate & Show (Any Language → RU/EN)**: Select text in **any language** (German, French, Spanish, Chinese, etc.) and press `Ctrl + E` to show a beautiful, modern dark-themed translation popup. If the text is Russian, it translates to English; otherwise, it translates to Russian.
*   **`Ctrl + G` — Screen Area Translation (OCR)**: Press `Ctrl + G` and drag a rectangle over any part of the screen (e.g., game chat history) to perform instant OCR and translate it.
*   **Zero Configuration**: Automatically detects if Windows OCR language packs (English/Russian) are missing and offers to install them in the background with a single click.
*   **Game-Safe**: Simulates keyboard inputs with native Windows API and optimized delays, preventing games from missing key strokes.
*   **UAC Elevated**: Automatically requests Administrator privileges at startup to work seamlessly over games running as Admin.

### 🚀 How to Install and Run
1.  Click the **Download** button above to go to the [Releases](https://github.com/kosolapkeen/quicktranslator/releases) page.
2.  Download the latest `QuickTranslator.exe` and run it.
3.  Windows will ask for Administrator privileges (required to send keystrokes to games).
4.  If you are running it for the first time, it will prompt you to install Windows OCR components. Click **Yes** and wait for the completion window.
5.  The program will sit quietly in your system tray.

### 🛠️ Build from Source
If you want to compile the executable yourself:
1.  Install Python 3.10+
2.  Install dependencies:
    ```bash
    pip install pynput pystray Pillow winocr
    ```
3.  Compile using PyInstaller:
    ```bash
    pyinstaller --clean --noconsole --onefile --uac-admin --icon="icon.ico" --name="QuickTranslator" translator_tray.py
    ```

---

## Русский

[![Скачать](https://img.shields.io/badge/%D0%A1%D0%BA%D0%B0%D1%87%D0%B0%D1%82%D1%8C-%D0%9F%D0%BE%D1%81%D0%BB%D0%B5%D0%B4%D0%BD%D0%B8%D0%B9%20%D0%A0%D0%B5%D0%BB%D0%B8%D0%B7-green?style=for-the-badge&logo=github)](https://github.com/kosolapkeen/quicktranslator/releases)

**Quick Translator** — это легкий, быстрый и безопасный для игр экранный и текстовый переводчик для Windows. Он работает в системном трее и специально оптимизирован для стабильной работы внутри игр (например, Minecraft) и других приложений.

### 🌟 Возможности
*   **`Ctrl + Q` — Перевести и Заменить (RU ↔ EN)**: Напишите сообщение на русском или английском, нажмите `Ctrl + Q`, и текст мгновенно заменится на перевод.
    *   *Умное выделение*: Если вы выделите конкретное слово, переведется только оно. Если ничего не выделено — переведется все поле ввода.
    *   *Примечание*: Этот хоткей работает строго для перевода между русским и английским языками.
*   **`Ctrl + E` — Перевести и Показать (Любой язык → RU/EN)**: Выделите текст на **любом языке мира** (немецком, французском, испанском, китайском и т.д.) и нажмите `Ctrl + E`, чтобы отобразить перевод в красивом окне. Если text русский — он переведется на английский, если на любом другом языке — на русский.
*   **`Ctrl + G` — Перевод области экрана (OCR)**: Нажмите `Ctrl + G` и выделите рамкой любую область экрана (например, историю чата игры), чтобы мгновенно распознать и перевести текст.
*   **Нулевая конфигурация**: Автоматически проверяет наличие языковых пакетов Windows OCR (русского и английского) при запуске и предлагает установить их в фоне в один клик.
*   **Безопасен для игр**: Эмулирует нажатия клавиш через низкоуровневый Windows API с оптимизированными задержками, благодаря чему игры не пропускают нажатия.
*   **Запуск от Администратора**: Автоматически запрашивает права Администратора при запуске, чтобы работать поверх игр, запущенных от Администратора.

### 🚀 Инструкция по установке и запуску
1.  Нажмите кнопку **Скачать** выше, чтобы перейти на страницу [Релизов](https://github.com/kosolapkeen/quicktranslator/releases).
2.  Скачайте файл `QuickTranslator.exe` и запустите его.
3.  Windows запросит права Администратора (это необходимо для отправки нажатий клавиш в игры).
4.  При первом запуске программа предложит установить компоненты Windows OCR. Нажмите **Да** и дождитесь окна об успешном завершении.
5.  Иконка программы появится в системном трее.

### 🛠️ Сборка из исходного кода
Если вы хотите скомпилировать файл самостоятельно:
1.  Установите Python 3.10+
2.  Установите зависимости:
    ```bash
    pip install pynput pystray Pillow winocr
    ```
3.  Скомпилируйте проект с помощью PyInstaller:
    ```bash
    pyinstaller --clean --noconsole --onefile --uac-admin --icon="icon.ico" --name="QuickTranslator" translator_tray.py
    ```

---

## 💖 Support / Поддержка

If you like this project, you can support the developer here:  
Если вам нравится этот проект, вы можете поддержать разработчика здесь:

👉 **[DonationAlerts](https://www.donationalerts.com/r/kosol4pkeen)** 👈
