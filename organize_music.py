import os
import shutil
import time
import sys
import threading
import mmap
from concurrent.futures import ThreadPoolExecutor, as_completed

def display_menu(title, options):
    print("\n" + "=" * 60)
    print(f"{title}")
    print("=" * 60)
    for key, option in options.items():
        print(f"{key}. {option['label']}")
    print("=" * 60)
    
    while True:
        choice = input("Enter your choice: ").strip()
        if choice in options:
            return choice
        print("Invalid choice. Please try again.")

def get_yes_no(prompt):
    while True:
        response = input(f"{prompt} (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        print("Please enter 'y' or 'n'")

def select_formats():
    options = {
        '1': {'label': "Process FLAC files only", 'formats': ['.flac']},
        '2': {'label': "Process AAC files only", 'formats': ['.m4a']},
        '3': {'label': "Process MP3 files only", 'formats': ['.mp3']},
        '4': {'label': "Process FLAC and AAC", 'formats': ['.flac', '.m4a']},
        '5': {'label': "Process FLAC and MP3", 'formats': ['.flac', '.mp3']},
        '6': {'label': "Process AAC and MP3", 'formats': ['.m4a', '.mp3']},
        '7': {'label': "Process ALL formats", 'formats': ['.flac', '.m4a', '.mp3']},
    }
    choice = display_menu("SELECT FORMATS TO PROCESS", options)
    return options[choice]['formats']

def select_output_mode():
    options = {
        '1': {'label': "Verbose mode (show all operations)", 'mode': 'verbose'},
        '2': {'label': "Progress bar (visual indicator)", 'mode': 'progress'},
        '3': {'label': "Minimal output (only important info)", 'mode': 'minimal'},
    }
    choice = display_menu("SELECT OUTPUT MODE", options)
    return options[choice]['mode']

def select_thread_count():
    cpu_count = os.cpu_count() or 4
    default_threads = min(cpu_count * 2, 16)
    
    print("\n" + "=" * 60)
    print("MULTITHREADING CONFIGURATION")
    print("=" * 60)
    print(f"Detected CPU cores: {cpu_count}")
    print(f"Recommended threads: {default_threads}")
    print("=" * 60)
    
    while True:
        try:
            threads = input(f"Enter number of threads to use (1-32, default {default_threads}): ").strip()
            if not threads:
                return default_threads
            threads = int(threads)
            if 1 <= threads <= 32:
                return threads
            print("Please enter a value between 1 and 32")
        except ValueError:
            print("Please enter a valid number")

def get_folder_deletion_preference():
    options = {
        '1': {'label': "Delete empty folders automatically", 'mode': 'auto'},
        '2': {'label': "Ask before deleting each folder", 'mode': 'ask'},
        '3': {'label': "Don't delete any folders", 'mode': 'none'},
    }
    choice = display_menu("FOLDER DELETION PREFERENCES", options)
    return options[choice]['mode']

def get_processing_confirmation(selected_formats, output_mode, delete_mode, thread_count):
    print("\n" + "=" * 60)
    print("PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Formats: {', '.join(selected_formats)}")
    print(f"Output: {output_mode.capitalize()} mode")
    print(f"Folder deletion: {delete_mode.capitalize()}")
    print(f"Threads: {thread_count}")
    print("=" * 60)
    return get_yes_no("Start processing?")

def scan_total_files(protected_paths, selected_formats):
    print("\nScanning files...")
    total_files = 0
    
    for root, _, files in os.walk('.'):
        abs_root = os.path.abspath(root)
        if any(abs_root.startswith(p) for p in protected_paths):
            continue
            
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in selected_formats or ext in ['.jpg', '.jpeg', '.png', '.cue', '.txt', '.log', '.nfo']:
                total_files += 1
                
    return total_files

def update_progress(progress, total, start_time):
    percent = (progress / total) * 100
    bar_length = 50
    filled_length = int(bar_length * progress // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    
    elapsed = time.time() - start_time
    if progress > 0:
        eta = (elapsed / progress) * (total - progress)
        eta_str = f"ETA: {eta:.1f}s"
    else:
        eta_str = "ETA: Calculating..."
    
    sys.stdout.write(f"\rProgress: |{bar}| {percent:.1f}% ({progress}/{total}) {eta_str}")
    sys.stdout.flush()

def copy_large_file(src, dst, buffer_size=16*1024*1024):
    try:
        with open(src, 'rb') as fsrc:
            with mmap.mmap(fsrc.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_src:
                with open(dst, 'wb') as fdst:
                    offset = 0
                    while offset < len(mmapped_src):
                        chunk = mmapped_src[offset:offset+buffer_size]
                        fdst.write(chunk)
                        offset += buffer_size
        shutil.copystat(src, dst)
        return True
    except Exception as e:
        print(f"Error copying {src}: {str(e)}")
        return False

def process_file(filepath, stats, selected_formats, output_mode, dir_lock, protected_paths):
    try:
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[1].lower()
        abs_filepath = os.path.abspath(filepath)
        
        if any(abs_filepath.startswith(p) for p in protected_paths):
            with stats['lock']:
                stats['skipped'] += 1
            return
            
        if ext in selected_formats:
            dest_root = stats['roots_map'][ext]
            rel_path = os.path.relpath(os.path.dirname(filepath), '.')
            dest_dir = os.path.join(dest_root, rel_path)
            dest_path = os.path.join(dest_dir, filename)
            
            if not os.path.exists(dest_dir):
                with dir_lock:
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir, exist_ok=True)
                        if output_mode == 'verbose':
                            print(f"Created directory: {dest_dir}")
            
            if not os.path.exists(dest_path):
                shutil.move(filepath, dest_path)
                with stats['lock']:
                    stats['audio'] += 1
                if output_mode == 'verbose':
                    print(f"Moved audio: {filepath} -> {dest_path}")
            else:
                with stats['lock']:
                    stats['skipped'] += 1
        
        elif ext in ['.jpg', '.jpeg', '.png', '.cue', '.txt', '.log', '.nfo']:
            copied = False
            for dest_root in stats['protected_roots']:
                rel_path = os.path.relpath(os.path.dirname(filepath), '.')
                dest_dir = os.path.join(dest_root, rel_path)
                dest_path = os.path.join(dest_dir, filename)
                
                if not os.path.exists(dest_dir):
                    with dir_lock:
                        if not os.path.exists(dest_dir):
                            os.makedirs(dest_dir, exist_ok=True)
                            if output_mode == 'verbose':
                                print(f"Created directory: {dest_dir}")
                
                if not os.path.exists(dest_path):
                    if os.path.getsize(filepath) > 10 * 1024 * 1024:
                        if copy_large_file(filepath, dest_path):
                            copied = True
                            with stats['lock']:
                                stats['non_audio'] += 1
                            if output_mode == 'verbose':
                                print(f"Copied large non-audio: {filepath} -> {dest_path}")
                    else:
                        shutil.copy2(filepath, dest_path)
                        copied = True
                        with stats['lock']:
                            stats['non_audio'] += 1
                        if output_mode == 'verbose':
                            print(f"Copied non-audio: {filepath} -> {dest_path}")
            
            if copied:
                try:
                    os.remove(filepath)
                    if output_mode == 'verbose':
                        print(f"Deleted original: {filepath}")
                except Exception as e:
                    with stats['lock']:
                        stats['errors'] += 1
                    if output_mode != 'minimal':
                        print(f"Error deleting {filepath}: {str(e)}")
    
    except Exception as e:
        with stats['lock']:
            stats['errors'] += 1
        if output_mode != 'minimal':
            print(f"\nError processing {filepath}: {str(e)}")
    
    with stats['lock']:
        stats['processed'] += 1
        if output_mode == 'progress' and stats['total_files'] > 0:
            update_progress(stats['processed'], stats['total_files'], stats['start_time'])

def main():
    PROTECTED_ROOTS = ['FLAC', 'AAC', 'MP3']
    ROOTS_MAP = {
        '.flac': 'FLAC',
        '.m4a': 'AAC',
        '.mp3': 'MP3'
    }
    
    print("\n" + "=" * 60)
    print("MULTITHREADED MUSIC LIBRARY ORGANIZER")
    print("=" * 60)
    print("Current directory: " + os.getcwd())
    print("\nPlease confirm this is the root of your music library.")
    
    if not get_yes_no("Is this the correct directory?"):
        print("\nOperation cancelled. Please place this script in your music library root.")
        input("\nPress Enter to exit...")
        return
    
    for root_name in PROTECTED_ROOTS:
        if not os.path.exists(root_name):
            os.makedirs(root_name, exist_ok=True)
    
    protected_paths = [os.path.abspath(p) for p in PROTECTED_ROOTS]
    
    selected_formats = select_formats()
    output_mode = select_output_mode()
    thread_count = select_thread_count()
    delete_mode = get_folder_deletion_preference()
    
    if not get_processing_confirmation(selected_formats, output_mode, delete_mode, thread_count):
        print("Processing cancelled by user.")
        return
    
    stats = {
        'audio': 0,
        'non_audio': 0,
        'skipped': 0,
        'errors': 0,
        'processed': 0,
        'start_time': time.time(),
        'lock': threading.Lock(),
        'roots_map': ROOTS_MAP,
        'protected_roots': PROTECTED_ROOTS
    }
    
    if output_mode == 'progress':
        with stats['lock']:
            stats['total_files'] = scan_total_files(protected_paths, selected_formats)
    else:
        stats['total_files'] = 0
    
    print("\nStarting processing with {} threads...".format(thread_count))
    
    dir_lock = threading.Lock()
    file_queue = []
    
    for root, _, files in os.walk('.'):
        abs_root = os.path.abspath(root)
        if any(abs_root.startswith(p) for p in protected_paths):
            continue
            
        for filename in files:
            filepath = os.path.join(root, filename)
            ext = os.path.splitext(filename)[1].lower()
            if ext in selected_formats or ext in ['.jpg', '.jpeg', '.png', '.cue', '.txt', '.log', '.nfo']:
                file_queue.append(filepath)
    
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(
            process_file, 
            filepath, 
            stats, 
            selected_formats, 
            output_mode,
            dir_lock,
            protected_paths
        ) for filepath in file_queue]
        
        for future in as_completed(futures):
            pass
    
    if output_mode == 'progress':
        print("\n")
    
    if delete_mode != 'none':
        print("\nCleaning empty folders...")
        empty_count = 0
        skipped_count = 0
        
        for root, dirs, files in os.walk('.', topdown=False):
            abs_root = os.path.abspath(root)
            if any(abs_root.startswith(p) for p in protected_paths) or root == '.':
                continue
                
            try:
                if not os.listdir(root):
                    if delete_mode == 'ask':
                        delete = get_yes_no(f"Delete empty folder: {root}?")
                    else:
                        delete = True
                    
                    if delete:
                        os.rmdir(root)
                        empty_count += 1
                        if output_mode != 'minimal':
                            print(f"Removed empty folder: {root}")
                    else:
                        skipped_count += 1
            except Exception as e:
                if output_mode != 'minimal':
                    print(f"Error checking {root}: {str(e)}")
        
        if output_mode != 'minimal':
            print(f"\nRemoved {empty_count} empty folders")
            if delete_mode == 'ask':
                print(f"Skipped {skipped_count} folders by user choice")
    
    elapsed = time.time() - stats['start_time']
    print("\n" + "=" * 60)
    print("PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Audio files processed: {stats['audio']}")
    print(f"Non-audio files handled: {stats['non_audio']}")
    print(f"Files skipped: {stats['skipped']}")
    print(f"Errors encountered: {stats['errors']}")
    print(f"Total files processed: {len(file_queue)}")
    print(f"Total processing time: {elapsed:.1f} seconds")
    print(f"Processing speed: {len(file_queue)/max(elapsed, 0.1):.1f} files/sec")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user")
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
    finally:
        input("\nPress Enter to exit...")
