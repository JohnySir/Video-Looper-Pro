import subprocess
import json
import os
import sys
import math
import shutil
import time
import threading
import itertools

# --- CONFIGURATION ---
# IMPORTANT: Change this path to where your mkvmerge.exe is located.
# Example for Windows: "C:/Program Files/MKVToolNix/mkvmerge.exe"
# If mkvmerge is in your system's PATH, you can just leave it as "mkvmerge".
MKVTOOLNIX_PATH = "C:\Program Files\MKVToolNix\mkvmerge.exe" 
# For best results, install FFmpeg and add it to your system's PATH.
# The script will auto-detect 'ffprobe.exe' if it's in the PATH.
# --- END CONFIGURATION ---

class Spinner:
    """A simple spinning cursor in the console."""
    def __init__(self, message="Processing...", delay=0.1):
        self.spinner = itertools.cycle(['-', '/', '|', '\\'])
        self.delay = delay
        self.message = message
        self.running = False
        self.spinner_thread = None

    def start(self):
        """Starts the spinner."""
        self.running = True
        self.spinner_thread = threading.Thread(target=self._spin)
        self.spinner_thread.start()

    def _spin(self):
        """The actual spinning logic."""
        while self.running:
            sys.stdout.write(f"\r{self.message} {next(self.spinner)}")
            sys.stdout.flush()
            time.sleep(self.delay)
        # Clear the line when done
        sys.stdout.write('\r' + ' ' * (len(self.message) + 2) + '\r')
        sys.stdout.flush()

    def stop(self):
        """Stops the spinner."""
        self.running = False
        if self.spinner_thread:
            self.spinner_thread.join()

def find_executable(name):
    """Checks if an executable like 'mkvmerge' or 'ffprobe' is in the system PATH."""
    if name == 'mkvmerge' and os.path.exists(MKVTOOLNIX_PATH):
        return MKVTOOLNIX_PATH

    executable = shutil.which(name)
    if executable:
        print(f"Found '{name}' in your system's PATH.")
        return executable
        
    return None

def get_duration_ffprobe(ffprobe_path, video_path):
    """Gets duration using ffprobe, which is generally more reliable."""
    command = [
        ffprobe_path, "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", video_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        video_info = json.loads(result.stdout)
        
        if "format" in video_info and "duration" in video_info["format"]:
            return float(video_info["format"]["duration"])
            
        if "streams" in video_info:
            for stream in video_info["streams"]:
                if stream.get("codec_type") == "video" and "duration" in stream:
                    return float(stream["duration"])
        return None
    except Exception:
        return None

def get_duration_mkvmerge(mkvmerge_path, video_path):
    """Gets duration using mkvmerge (the original fallback method)."""
    command = [mkvmerge_path, "-J", video_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        video_info = json.loads(result.stdout)
        duration_ns = None

        if "container" in video_info and "properties" in video_info["container"]:
            duration_ns = video_info["container"]["properties"].get("duration")
        
        if duration_ns is None and "tracks" in video_info:
            for track in video_info["tracks"]:
                if track.get("type") == "video" and "properties" in track and "duration" in track["properties"]:
                    duration_ns = track["properties"].get("duration")
                    if duration_ns:
                        break
        
        if duration_ns:
            return duration_ns / 1_000_000_000.0
        return None
    except Exception:
        return None

def get_video_duration(mkvmerge_path, ffprobe_path, video_path):
    """
    Gets the duration of a video file in seconds.
    Tries using ffprobe first for reliability, then falls back to mkvmerge.
    """
    print("\nAnalyzing video file to get its duration...")
    duration_sec = None

    if ffprobe_path:
        print("-> Attempting to get duration with ffprobe (recommended)...")
        duration_sec = get_duration_ffprobe(ffprobe_path, video_path)
        if duration_sec is not None:
            return duration_sec

    if mkvmerge_path:
        print("-> ffprobe failed or not found. Falling back to mkvmerge...")
        duration_sec = get_duration_mkvmerge(mkvmerge_path, video_path)
        if duration_sec is not None:
            return duration_sec

    print("\nError: Could not determine video duration using any available method.")
    print("For best results, please ensure FFmpeg (for ffprobe) is installed and in your system's PATH.")
    return None

def get_user_inputs():
    """Prompts the user for the video path and target duration."""
    video_path = ""
    while not os.path.isfile(video_path):
        video_path = input("Enter the full path to your video file: ").strip().strip('"')
        if not os.path.isfile(video_path):
            print("File not found. Please check the path and try again.")
            
    target_hours = 0
    while target_hours <= 0:
        try:
            target_hours = float(input("Enter the target duration in hours (e.g., 1, 2.5, 10): "))
            if target_hours <= 0:
                print("Please enter a positive number for the hours.")
        except ValueError:
            print("Invalid input. Please enter a number.")
            
    return video_path, target_hours

def merge_videos_iteratively(mkvmerge_path, source_video, output_video, total_loops):
    """
    Merges a video with itself iteratively to avoid command line length limits.
    Uses a doubling strategy for efficiency. Returns True on success, False on failure.
    """
    if total_loops <= 0:
        return False
    if total_loops == 1:
        print("Number of loops is 1. Copying file instead of merging.")
        try:
            shutil.copy(source_video, output_video)
            return True
        except Exception as e:
            print(f"Error copying file: {e}")
            return False

    spinner = Spinner("Merging video (this might take a while)...")
    spinner.start()

    temp_files = []
    base_dir = os.path.dirname(os.path.abspath(output_video))
    base_name, ext = os.path.splitext(os.path.basename(output_video))

    def get_temp_path(index):
        path = os.path.join(base_dir, f"{base_name}_temp_{index}{ext}")
        temp_files.append(path)
        return path

    try:
        # --- Doubling Phase ---
        # Create power-of-2 looped videos (2x, 4x, 8x, etc.)
        power_of_2_files = {1: source_video}
        loops_doubled = 1
        temp_idx = 0

        while (loops_doubled * 2) <= total_loops:
            input_file = power_of_2_files[loops_doubled]
            output_file = get_temp_path(temp_idx)
            temp_idx += 1
            
            command = [mkvmerge_path, '-o', output_file, '(', input_file, ')', '+', '(', input_file, ')']
            
            process = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8')
            if process.returncode != 0:
                spinner.stop()
                print(f"\nError during doubling phase (merging {loops_doubled}x file).")
                print("--- mkvmerge output ---\n" + (process.stderr or "No error output.") + "\n-----------------------")
                return False
            
            loops_doubled *= 2
            power_of_2_files[loops_doubled] = output_file

        # --- Assembly Phase ---
        # Combine the generated power-of-2 files to reach the exact loop count
        files_to_merge = []
        remaining_loops = total_loops

        for power in sorted(power_of_2_files.keys(), reverse=True):
            if remaining_loops >= power:
                files_to_merge.append(power_of_2_files[power])
                remaining_loops -= power
        
        if len(files_to_merge) == 1:
             shutil.move(files_to_merge[0], output_video)
        else:
            final_command = [mkvmerge_path, '-o', output_video, '(', files_to_merge[0], ')']
            for file_to_add in files_to_merge[1:]:
                final_command.extend(['+', '(', file_to_add, ')'])
            
            process = subprocess.run(final_command, capture_output=True, text=True, check=False, encoding='utf-8')
            if process.returncode != 0:
                spinner.stop()
                print("\nError during final assembly phase.")
                print("--- mkvmerge output ---\n" + (process.stderr or "No error output.") + "\n-----------------------")
                return False

        spinner.stop()
        return True

    except Exception as e:
        spinner.stop()
        print(f"\nAn unexpected error occurred during the merge process: {e}")
        return False
    finally:
        # --- Cleanup Phase ---
        print("Cleaning up temporary files...")
        for f in temp_files:
            if os.path.exists(f) and f != source_video:
                try:
                    os.remove(f)
                except Exception as e:
                    print(f"Warning: Could not remove temporary file {f}: {e}")

def main():
    """Main function to run the video looping script."""
    print("--- Video Looper With MKVToolNix & FFmpeg by Johny Sir---")
    
    mkvmerge_exec = find_executable("mkvmerge")
    ffprobe_exec = find_executable("ffprobe")

    if not mkvmerge_exec:
        print("\nFatal Error: 'mkvmerge' not found.")
        print(f"Please ensure MKVToolNix is installed and correctly configured in the script or system PATH.")
        input("Press Enter to exit.")
        return
        
    if not ffprobe_exec:
        print("\nWarning: 'ffprobe' not found. For best results, install FFmpeg from https://ffmpeg.org/download.html")
        print("Proceeding with mkvmerge only, which may fail on some files.")

    video_path, target_hours = get_user_inputs()
    if not video_path:
        return

    duration_sec = get_video_duration(mkvmerge_exec, ffprobe_exec, video_path)
    if duration_sec is None:
        input("Press Enter to exit.")
        return
        
    print(f"\nVideo duration: {duration_sec:.2f} seconds (~{duration_sec/60:.2f} minutes).")

    target_sec = target_hours * 3600
    if duration_sec == 0:
        print("Error: Video duration is zero. Cannot proceed.")
        input("Press Enter to exit.")
        return
        
    num_loops = math.ceil(target_sec / duration_sec)
    final_duration_hours = (num_loops * duration_sec) / 3600

    print(f"To reach {target_hours} hours, the video will be looped {num_loops} times.")
    print(f"The final video will be approximately {final_duration_hours:.2f} hours long.")
    
    if input("Do you want to proceed? (y/n): ").lower() != 'y':
        print("Operation cancelled.")
        return

    path_parts = os.path.splitext(video_path)
    output_path = f"{path_parts[0]}_looped_{int(target_hours)}hr{path_parts[1]}"

    print(f"\nStarting merge process. Output file will be:\n{output_path}")
    
    success = merge_videos_iteratively(mkvmerge_exec, video_path, output_path, num_loops)
    
    if success:
        print("\n✅ Success! Video looped successfully.")
    else:
        print("\n❌ Error: The merge process failed. Please check the output above for details.")

    input("\nPress Enter to exit.")

if __name__ == "__main__":
    main()
