import os
import sys
import shutil
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

def find_ffmpeg():
    """Locate ffmpeg executable in PATH or WinGet packages directory."""
    # 1. Check standard PATH
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        # Return the directory containing ffmpeg executable
        return os.path.dirname(ffmpeg_path)
    
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

def check_dependencies():
    """Verify that all external dependencies (ffmpeg, node/deno JS runtimes) are installed."""
    print("[*] Проверка системных зависимостей...")
    
    # 1. Check ffmpeg
    ffmpeg_loc = find_ffmpeg()
    
    # 2. Check JavaScript runtimes (node, deno)
    js_runtime = shutil.which("node") or shutil.which("deno")
    
    dependencies_ok = True
    
    if not ffmpeg_loc:
        print("\n[ВНИМАНИЕ] ffmpeg не найден в вашей системе!")
        print("  -> Без него невозможно конвертировать скачанное аудио в формат MP3.")
        print("  -> Способ установки: откройте PowerShell от Администратора и запустите:")
        print("     winget install Gyan.FFmpeg")
        dependencies_ok = False
    else:
        print("  [+] ffmpeg: найден")
        
    if not js_runtime:
        print("\n[ВНИМАНИЕ] Среда JavaScript (Node.js / Deno) не найдена в системе!")
        print("  -> Без нее YouTube будет блокировать скачивание некоторых видео (ошибка 403 / Requested format is not available).")
        print("  -> Способ установки: откройте PowerShell от Администратора и запустите:")
        print("     winget install OpenJS.NodeJS")
        dependencies_ok = False
    else:
        print("  [+] Среда JavaScript (Node.js/Deno): найдена")
        
    if not dependencies_ok:
        print("\n[Ошибка] Не все обязательные зависимости установлены.")
        print("Пожалуйста, установите недостающие пакеты командами выше и перезапустите программу.")
        sys.exit(1)
        
    print("[+] Все зависимости проверены успешно!\n")
    return ffmpeg_loc

def postprocessor_hook(d):
    """Callback triggered on post-processing milestones. Prints a green line on success."""
    if d['status'] == 'finished' and d['postprocessor'] == 'ExtractAudio':
        title = d['info_dict'].get('title', 'Unknown Title')
        # ANSI escape sequence for bold green: \033[1;32m and reset: \033[0m
        print(f"\n\033[1;32m[+] Успешно скачан и конвертирован трек: {title}\033[0m\n")

def main():
    # Initialize ANSI escape sequences support in Windows Console/PowerShell
    if os.name == 'nt':
        os.system('')
        
    print("=" * 60)
    print("   YT2MP3 Scraper (yt-dlp + ffmpeg)")
    print("=" * 60)
    
    # Verify and locate dependencies (ffmpeg and JS runtime)
    ffmpeg_loc = check_dependencies()
        
    # Get YouTube URL
    url = input("Введите ссылку на YouTube-канал, плейлист или видео: ").strip()
    if not url:
        print("[Ошибка] Ссылка не может быть пустой.")
        sys.exit(1)
        
    # Get browser for cookies
    browser = get_browser_choice()
    
    # Output template: Music/<Channel Name>/<Video Title>.mp3
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
        'postprocessor_hooks': [postprocessor_hook],
        # Polite downloading: sleep between files
        'sleep_interval': 5,
        'max_sleep_interval': 15,
        'ffmpeg_location': ffmpeg_loc,
        # Emulate browser TLS fingerprint so that 'zapret' can bypass DPI correctly
        'impersonate': ImpersonateTarget.from_str('chrome'),
        'http_backend': 'curl_cffi',
        # Retries configurations to punch through unstable network connections/blocks
        'retries': 10,
        'fragment_retries': 10,
        # Emulate headers of Opera browser to match user's environment and TLS fingerprint
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 OPR/112.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        },
        # Use Smart TV clients first to bypass PO Token/403 requirements for audio
        'extractor_args': {
            'youtube': {
                'player_client': ['tv', 'tv_embedded', 'android', 'web']
            }
        }
    }
    
    # Inject browser cookies if selected
    if browser:
        print(f"[*] Будут использованы куки браузера: {browser}")
        ydl_opts['cookiesfrombrowser'] = (browser,)
        
    print("\n[*] Запуск процесса скачивания...")
    print("[*] Треки будут сохранены в папку 'Music/<Название канала>/'")
    print(f"[*] Список скачанных видео сохраняется в {archive_path}")
    print("=" * 60)
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            exit_code = ydl.download([url])
            if exit_code == 0:
                print("\n[+] Процесс скачивания успешно завершен!")
            else:
                print("\n[!] Процесс завершился с предупреждениями или ошибками (некоторые видео могли быть пропущены).")
    except Exception as e:
        err_msg = str(e) if str(e) else f"Internal error ({type(e).__name__})"
        print(f"\n[Критическая ошибка] Не удалось выполнить скачивание: {err_msg}")
        # Print a warning if it looks like a connection/blocking issue
        err_str = str(e).lower()
        if "10054" in err_str or "10060" in err_str or "timeout" in err_str or "reset" in err_str or "connection" in err_str:
            print("\n[!] Не получается достучаться до серверов YouTube.")
            print("    Проверьте подключение к интернету или работу средств обхода блокировок (VPN/GoodbyeDPI).")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Скачивание прервано пользователем.")
        sys.exit(0)
