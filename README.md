# 🎬 Video Looper Pro 🔁

A simple yet powerful Python script to loop any video file for hours, creating those epic 1-hour or 10-hour meme videos you see on YouTube! 🤣

## ✨ Features

-   **Endless Loops**: Turn a short clip into a multi-hour marathon.
-   **Smart & Robust**: Uses a "doubling" merge strategy to avoid command-line limits, even for hundreds of loops! 🧠
-   **Best-in-Class Tools**: Relies on `ffprobe` (from FFmpeg) for accurate video analysis and `mkvmerge` for the heavy lifting.
-   **User-Friendly**: Simple command-line prompts guide you through the process.
-   **Keeps You Informed**: A spinning cursor 🔄 shows that the script is hard at work and hasn't crashed.
-   **Automatic Cleanup**: Deletes temporary files after the merge is complete. 🧹

## 🛠️ Requirements

1.  **Python 3**: Make sure you have Python installed.
2.  **MKVToolNix**: Required for the core merging functionality.
    -   [Download Here](https://mkvtoolnix.download/)
    -   Ensure `mkvmerge.exe` is in your system's PATH or set the path directly in the script.
3.  **FFmpeg** (Highly Recommended): For the most reliable video duration detection.
    -   [Download Here](https://ffmpeg.org/download.html)
    -   Ensure `ffprobe.exe` is in your system's PATH.

## 🚀 How to Use

1.  **Clone or Download**: Get the `video_looper.py` script onto your computer.
2.  **Install Requirements**: Make sure MKVToolNix and FFmpeg are installed and accessible via your system's PATH.
3.  **Run the Script**: Open your terminal or command prompt and run the script:
    ```bash
    python video_looper.py
    ```
4.  **Follow the Prompts**:
    -   Paste the full path to your video file.
    -   Enter the desired final length in hours (e.g., `1`, `2.5`, `10`).
    -   Confirm, and let the magic happen! ✨

The final looped video will be saved in the same directory as your original file. Enjoy creating! 🎉
