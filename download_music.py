import os
import sys
import shutil
import yt_dlp

def find_ffmpeg():
    """Locate ffmpeg executable in PATH or WinGet packages directory."""
    # 1. Check standard PATH
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    
    # 2. Check WinGet installation path (useful if PATH wasn't updated yet)
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        winget_packages = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages")
        if os.path.exists(winget_packages):
            for item in os.listdir(winget_packages):
                if item.startswith("Gyan.FFmpeg"):
                    pkg_path = os.path.join(winget_packages, item)
                    # Walk to find the bin directory containing ffmpeg.exe
                    for root, dirs, files in os.walk(pkg_path):
                        if "ffmpeg.exe" in files:
                            print(f"[*] Найден ffmpeg в папке WinGet: {root}")
                            return root
    return None

def get_browser_choice():
    """Prompt the user to choose a browser for cookies, or skip."""
    print("\n[?] Хотите ли вы использовать куки вашего браузера для скачивания?")
    print("    Это полезно для спонсорских видео (если вы спонсор), приватных плейлистов или обхода ограничений возраста.")
    print("    0. Нет, скачивать без куков (по умолчанию)")
    print("    1. Google Chrome")
    print("    2. Mozilla Firefox")
    print("    3. Microsoft Edge")
    print("    4. Opera")
    print("    5. Brave")
    
    choice = input("Выберите вариант (0-5) [0]: ").strip()
    if choice == "1":
        return "chrome"
    elif choice == "2":
        return "firefox"
    elif choice == "3":
        return "edge"
    elif choice == "4":
        return "opera"
    elif choice == "5":
        return "brave"
    return None

def get_proxy_choice():
    """Prompt the user for a proxy configuration."""
    print("\n[?] Нужен ли прокси для обхода блокировок YouTube в вашем регионе?")
    print("    Если у вас запущен GoodbyeDPI или глобальный VPN, прокси вводить не нужно.")
    print("    Нажмите Enter, чтобы продолжить без прокси.")
    proxy = input("Введите адрес прокси (например, socks5://127.0.0.1:1080 или http://127.0.0.1:8080): ").strip()
    return proxy if proxy else None

def main():
    print("=" * 60)
    print("   YouTube Music Downloader (yt-dlp + ffmpeg)")
    print("=" * 60)
    
    # Locate ffmpeg
    ffmpeg_loc = find_ffmpeg()
    if not ffmpeg_loc:
        print("[Внимание] ffmpeg не найден в системе. Скрипт не сможет конвертировать видео в MP3!")
        print("Пожалуйста, убедитесь, что установка через 'winget install Gyan.FFmpeg' завершилась успешно.")
        sys.exit(1)
        
    # Get YouTube URL
    url = input("Введите ссылку на YouTube-канал, плейлист или видео: ").strip()
    if not url:
        print("[Ошибка] Ссылка не может быть пустой.")
        sys.exit(1)
        
    # Get browser for cookies
    browser = get_browser_choice()
    
    # Get proxy config
    proxy = get_proxy_choice()
    
    # Output template: Music/<Channel Name>/<Video Title>.mp3
    # Use %(channel,uploader|Unknown_Channel)s to handle cases where channel name is missing
    out_template = os.path.join("Music", "%(channel,uploader|Unknown_Channel)s", "%(title)s.%(ext)s")
    archive_path = os.path.join("Music", "archive.txt")
    
    # Ensure Music directory exists
    os.makedirs("Music", exist_ok=True)
    
    # yt-dlp configuration options
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_template,
        'download_archive': archive_path,
        'ignoreerrors': True,  # Skip errors (like member-only videos) and continue
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',  # Optimal quality / file size ratio
        }],
        # Anti-blocking options
        'sleep_interval': 5,          # Minimum sleep between downloads in seconds
        'max_sleep_interval': 15,     # Maximum sleep between downloads in seconds
        'ffmpeg_location': ffmpeg_loc,
        # Bypass YouTube limitations in Russia (using alternative clients)
        'extractor_args': {
            'youtube': {
                'player_client': ['android_creator', 'web_creator']
            }
        }
    }
    
    # Inject browser cookies if selected
    if browser:
        print(f"[*] Будут использованы куки браузера: {browser}")
        ydl_opts['cookiesfrombrowser'] = (browser,)
        
    # Inject proxy if selected
    if proxy:
        print(f"[*] Будет использован прокси: {proxy}")
        ydl_opts['proxy'] = proxy
        
    print("\n[*] Запуск процесса скачивания...")
    print("[*] Треки будут сохранены в папку 'Music/<Название канала>/'")
    print(f"[*] Список уже скачанных видео сохраняется в {archive_path}")
    print("[*] Между скачиваниями будут случайные паузы (5-15 секунд) для защиты от блокировок.")
    print("=" * 60)
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            exit_code = ydl.download([url])
            if exit_code == 0:
                print("\n[+] Процесс скачивания успешно завершен!")
            else:
                print("\n[!] Процесс завершился с предупреждениями или ошибками (некоторые видео могли быть пропущены).")
    except Exception as e:
        print(f"\n[Критическая ошибка] Произошел сбой при работе yt-dlp: {e}")
        # Explain connection issues (e.g. WinError 10054)
        if "10054" in str(e) or "reset" in str(e).lower():
            print("\n[Совет] Ошибка часто возникает из-за блокировки YouTube в РФ.")
            print("Попробуйте включить VPN, GoodbyeDPI или настроить прокси в скрипте.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Скачивание прервано пользователем.")
        sys.exit(0)
