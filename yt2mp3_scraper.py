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
    print("    1. Opera")
    print("    2. Mozilla Firefox")
    
    choice = input("Выберите вариант (0-2) [0]: ").strip()
    if choice == "1":
        return "opera"
    elif choice == "2":
        return "firefox"
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

class DownloadStats:
    def __init__(self):
        self.new_downloads = []       # List of titles of newly downloaded songs
        self.skipped_archive = []     # List of titles/IDs skipped by archive
        self.failed_downloads = []    # List of unique error strings

stats = DownloadStats()

class YdlLogger:
    def debug(self, msg):
        if "has already been recorded in the archive" in msg:
            cleaned = msg.replace("[download] ", "").replace("has already been recorded in the archive", "").strip()
            stats.skipped_archive.append(cleaned)
        print(msg)

    def info(self, msg):
        print(msg)

    def warning(self, msg):
        print(msg, file=sys.stderr)

    def error(self, msg):
        cleaned_err = msg.replace("ERROR: ", "").strip()
        # Avoid duplicate messages in failed list
        if cleaned_err not in stats.failed_downloads:
            stats.failed_downloads.append(cleaned_err)
        print(msg, file=sys.stderr)

# Global set to track printed video IDs and prevent duplicate success lines
_printed_videos = set()

def postprocessor_hook(d):
    """Callback triggered on post-processing milestones. Prints a green line on success."""
    if d['status'] == 'finished' and d['postprocessor'] == 'ExtractAudio':
        video_id = d['info_dict'].get('id')
        if video_id and video_id not in _printed_videos:
            _printed_videos.add(video_id)
            title = d['info_dict'].get('title', 'Unknown Title')
            stats.new_downloads.append(title)
            # ANSI escape sequence for bold green: \033[1;32m and reset: \033[0m
            print(f"\n\033[1;32m[+] Успешно скачан и конвертирован трек: {title}\033[0m\n")

def print_summary():
    """Print a clean colorized download summary to the console."""
    print("\n" + "=" * 60)
    print("   СТАТИСТИКА ЗАГРУЗКИ / DOWNLOAD SUMMARY")
    print("=" * 60)
    
    total_processed = len(stats.new_downloads) + len(stats.skipped_archive) + len(stats.failed_downloads)
    
    print(f"Всего обработано видео: {total_processed}")
    
    if stats.new_downloads:
        print(f"\n\033[1;32m[+] Успешно скачано новых треков ({len(stats.new_downloads)}):\033[0m")
        for title in stats.new_downloads:
            print(f"    - {title}")
            
    if stats.skipped_archive:
        print(f"\n\033[1;36m[i] Пропущено (уже скачаны ранее) ({len(stats.skipped_archive)}):\033[0m")
        # List if small, otherwise just summary
        if len(stats.skipped_archive) <= 10:
            for title in stats.skipped_archive:
                print(f"    - {title}")
        else:
            # Print first 5 and last 5 or just counts
            print(f"    - всего {len(stats.skipped_archive)} файлов (список сохранен в Music/archive.txt)")
        
    if stats.failed_downloads:
        print(f"\n\033[1;31m[-] Не удалось скачать ({len(stats.failed_downloads)}):\033[0m")
        for err in stats.failed_downloads:
            print(f"    - {err}")
            
    print("=" * 60 + "\n")

def main():
    # Inject default installation path of Node.js to PATH to avoid WindowsApps execution alias conflicts
    node_default_path = "C:\\Program Files\\nodejs"
    if os.path.exists(node_default_path):
        os.environ["PATH"] = node_default_path + os.path.pathsep + os.environ.get("PATH", "")

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
        'logger': YdlLogger(),
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
        # Allow yt-dlp to use Node.js (by default it only enables Deno)
        'js_runtimes': {'node': {}, 'deno': {}},
        # Emulate headers of Opera browser to match user's environment and TLS fingerprint
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 OPR/112.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        },
        # Bypass heavy auth check on playlist/channel pages when using cookies to avoid DPI resets
        'extractor_args': {
            'youtubetab': {
                'skip': ['authcheck']
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
            
        # Print download statistics summary
        print_summary()
        
        if exit_code == 0:
            print("[+] Процесс скачивания успешно завершен!")
        else:
            print("[!] Процесс завершился с предупреждениями или ошибками (некоторые видео могли быть пропущены).")
    except Exception as e:
        # Also print whatever summary we managed to gather before crashing
        print_summary()
        err_msg = str(e) if str(e) else f"Internal error ({type(e).__name__})"
        print(f"[Критическая ошибка] Не удалось выполнить скачивание: {err_msg}")
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
