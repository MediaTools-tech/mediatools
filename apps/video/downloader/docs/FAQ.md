# FAQ - Video Downloader

---

## ❓ General Questions

**❓ Is MediaTools Video Downloader free?**  
Yes, MediaTools Video Downloader is open-source and free to use under the MIT License.

**❓ Which websites are supported?**  
yt-dlp supports 1000+ sites.  
For the complete current list, check: <https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md>

**❓ Do I need to install Python?**  
No, the application is self-contained and includes all necessary components.

**❓ Is my data collected or shared?**  
No. The application does not collect, store, or transmit any personal data. All processing happens locally on your computer.

**❓ My antivirus flags the application - is it safe?**  
Yes, this is a common false positive with applications that download executables (yt-dlp/FFmpeg). The application is open-source and completely safe. You may need to add an exception in your antivirus software.

**❓ Why can't I download from some websites?**  

- The website may not be supported by yt-dlp
- Regional restrictions may block access
- Some sites require cookies for authentication
- Check the [yt-dlp supported sites list](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) for compatibility

---

## 🛠 Installation & Setup

**❓ What if I skip downloading yt-dlp and ffmpeg?**  
**yt-dlp:** The application cannot function without yt-dlp. You have two options:

- Either allow the application to automatically download yt-dlp when prompted
- Or manually download yt-dlp from [yt-dlp official repository](https://github.com/yt-dlp/yt-dlp) and place the executable in the `bin/` folder

**FFmpeg:** The application can work without FFmpeg, but with limitations:

- Format 'b' (pre-merged streams) will work without FFmpeg, though these may not offer the best available quality
- Video merging (bestvideo+bestaudio) requires FFmpeg
- Format conversion requires FFmpeg
- Advanced features like post-processing require FFmpeg
- Audio format conversion requires FFmpeg

**❓ How to fix "yt-dlp not found" error?**  

1. App → Settings → Reset to defaults, Restart App
2. Allow app to download yt-dlp automatically
3. **Manual solution:**
   - Download yt-dlp from the [official releases page](https://github.com/yt-dlp/yt-dlp/releases)
   - Place the executable (`yt-dlp` or `yt-dlp.exe`) in the `bin/` folder
   - Restart the application

---

## ⚡ Download Performance

**❓ What download speed should I set?**  
**✅ 5M (5 Mbps) is recommended for most users because:**

- Conservative: Unlikely to be blocked by servers
- Stable: Provides consistent download performance
- Network-friendly: Doesn't monopolize your internet connection
- Reliable: Works well with most hosting platforms

**❌ Higher speeds (10M-20M) may work but risk:**

- Server blocking: Some platforms detect and block high-speed downloads
- IP throttling: Your IP might be temporarily limited

Adjust based on your: Internet plan, network stability, and target platform policies.

**❓ Can I change the download folder?**  
Yes. Go to Settings → Download Path and select a new folder. Make sure you have write permission to that location.

**❓ Why does progress bar run multiple times for a single video download?**  
This is normal behavior indicating separate component downloads:

1. Video stream - Main video content
2. Audio stream - Separate audio track
3. Thumbnail - Video preview image
4. Metadata - Video information

The application downloads these components then merges them into the final file.

## ❓ Why does download fail when the platform is supported by yt-dlp and I can see the video in my browser?

This is a common issue that can happen for several reasons:

### 🔒 Platform Anti-Bot Measures

**Many platforms actively block automated downloads:**

- Uses sophisticated bot detection
- May throttle downloads from certain IP ranges
- Require cookies from a logged-in session
- May need authentication or has rate limits

**Solution**:

- **Update yt-dlp** (if Auto-Update is disabled in settings)
- **Provide browser profile path** in Settings (recommended - use your actual browser session profile path)
- **Use cookies.txt file** (advanced users only - be aware of security risks when sharing cookies)

---

## 🔄 Queue & Session Management

**❓ Why is my queue from previous session not showing up?**  
Ensure "Multisession queue support" is enabled:

1. Go to Settings
2. Enable "Multisession queue support"
3. Restart the application

This feature must be enabled to preserve your download queue between sessions.

**❓ Why does Windows Explorer slow down with download folder?**  
This can occur when partially downloaded files accumulate:

**Cause:** With multisession support enabled, paused and ignored/skipped downloads create temporary files

**Solution:**

1. Complete or cancel pending downloads
2. Manually clean the download folder periodically
3. The application includes robust cleanup, but manual intervention may be needed for skipped downloads

**❓ Why do some URLs in my queue have "audio:" prefix?**  
This is how the application distinguishes between video and audio downloads:

- **Normal URL:** `https://youtube.com/video` = Video download
- **Prefixed URL:** `audio:https://youtube.com/video` = Audio download
- **Purpose:** Allows the same URL to be used for both video and audio downloads
- **Manual Editing:** You can add/remove the "audio:" prefix in `Queue.txt` to change download type

---

## 📁 Format & Container Issues

**❓ Which format should I choose?**

- **MKV:** Highest quality, supports pause/resume, better for archival
- **MP4:** Best compatibility (phones, tablets, social media), smaller file sizes
- **Single best (b):** Fastest download, no merging required, but may compromise on quality

**❓ Why are MKV files bigger?**  
MKV files are often bigger because they are commonly used to store the highest quality video and audio available, including lossless audio tracks. MP4 files are more focused on broad compatibility and are typically compressed more for smaller file sizes.

**❓ Why is pause/resume not supported for MP4 format?**  
Technical limitation of MP4 container:

- **MKV:** Supports true pause/resume at any point
- **MP4:** The MP4 container format doesn't support efficient resuming of partial downloads like MKV does. Resuming MP4 downloads often requires re-downloading significant portions
- **MP4:** Can only resume from certain checkpoints

**❓ How can I pause playlist download with MP4 as pause isn't supported?**  
You can pause (functionally), with caveats (With - Multisession queue support):

- With MP4 merge format, Playlist progress is saved between sessions (exit and restart)
- Already downloaded videos will not be downloaded again when you restart downloader
- Only last partially downloaded video (at exit time) will be downloaded again to continue playlist download

Ensure: "Multisession queue support" is enabled. The application will remember your position in the playlist and only overwrite the currently downloading video if interrupted.

**❓ Why isn't thumbnail showing for MKV files?**  
MKV thumbnails require external system support:

- **Windows:** Install [Icaros](https://www.majorgeeks.com/files/details/icaros.html) to enable MKV thumbnail previews in File Explorer
- **Linux:** Most modern file managers (Nautilus, Dolphin) support MKV thumbnails natively
- **Note:** This is a Windows Explorer limitation, not an application issue. The thumbnails are embedded correctly in the files.

---

## 🎵 Audio Download Questions (New in v2.0.0)

**❓ Where are audio files stored?**  
All audio downloads are automatically saved to:  
`[Your Downloads Folder]/Audio/`

**❓ Why does downloading MP3 after M4A replace the file instead of creating both?**  
This is yt-dlp behavior, not a bug:

- When you download a lower quality format after a higher quality one
- yt-dlp transcodes the existing file to the new format
- This prevents duplicate content but may reduce quality
- **Solution:** Download lower quality formats first(MP3), then higher quality(M4A) if both formats needed

**❓ Which audio format should I choose?**  

- **M4A:** Best balance of quality and compatibility (recommended)
- **MP3:** Universal compatibility, works on all devices
- **Best Audio:** Highest quality, but format may vary

**❓ Can I download both video and audio from the same URL?**  
Yes, you can download both video and audio from the same URL, you need to add URL twice, fisrt as "Download Video" and secondly as "Download Audio". Use the queue system to download both separately if needed.

**❓ Why are some audio files much larger than others?**  
Audio file size depends on:

- Source quality and bitrate
- Audio format and compression
- Duration of the audio
- Embedded metadata and thumbnails

**❓ How do I enable/disable thumbnails for audio files?**  
Go to Settings → Audio Settings → "Embed Thumbnail in Audio" toggle

**❓ Why is M4A format recommended over MP3?**  
M4A (AAC) is technically superior because:

- **More modern codec** (developed as MP3 successor)
- **Better compression efficiency** - higher quality at same file size
- **Improved handling of high frequencies** - less "muffling" effect
- **Better performance at lower bitrates**

**❓ Audio files missing thumbnails?**  

- Check if "Embed Thumbnail in Audio" is enabled in Settings
- Some sources may not provide cover art
- Thumbnail embedding requires FFmpeg

---

## 🎵 Spotdl (New in v2.1.0)

**❓ How spotdl downloads from Spotify?**  
URLs/tracks not downloaded directly from Spotify, spotdl extracts metadata from spotify url and then internally calls ytdlp to download corresponding track from some other source, you need to provide your Spotify API credentials (Client ID and Secret) in the application's settings. This is required to fetch metadata for tracks, albums, and playlists.

**❓ Why do I need a Spotify account?**  
A Spotify account is necessary to create an application on the Spotify Developer Dashboard, which in turn allows you to get a Client ID and Secret. These credentials are used by the application to access Spotify's metadata.

**❓ How to get Spotify Client ID and Secret?**  

1. Create a free user account on [Spotify](https://www.spotify.com/).
2. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
3. Create a new application.
4. You will find your Client ID and Client Secret in the application's settings.
5. For a detailed guide, you can watch any YouTube video on this topic.

**❓ Why am I getting an error when downloading a private Spotify playlist?**  
To download private or collaborative playlists, you need to enable the OAuth flow.

1. Go to your application on the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Click on "Edit Settings".
3. Under "Redirect URIs", enter `http://127.0.0.1:8000/callback`.
4. Save the settings.
5. In the application's settings, enable the "Enable Spotify Playlist Downloads" option.

---

## 🛠 Technical Questions

**❓ Where are my downloads stored?**  
Default paths - for installable and portable versions:

- **Windows:** `%LOCALAPPDATA%\Video Downloader\downloads\` or app folder
- **Linux:** `~/downloads/` or `~/.local/share/Video Downloader/downloads/`
- **macOS:** `~/downloads/` or application directory
- **Audio Files:** `[Downloads Folder]/Audio/`
- **Video Files:** `[Downloads Folder]/Video/`

**❓ Where are application settings stored?**

- **Windows:** `%LOCALAPPDATA%\Video Downloader\data`
- **Linux:** `~/.local/share/Video Downloader/data`
- **macOS:** `~/Library/Application Support/Video Downloader/data`

**❓ Can I run multiple instances?**  
No, only one instance can run at a time to prevent conflicts.

**❓ Does it support proxy servers?**  
Not currently through the GUI. Advanced users can configure yt-dlp's proxy settings manually.

---

## 🔧 Advanced Topics

**❓ Why are some videos downloading slowly despite fast internet?**  
**Common causes:**

1. Server limitations: Source platform may throttle downloads
2. Geographic restrictions: Content delivery network delays
3. Format availability: Higher quality formats may have limited bandwidth
4. Network congestion: Other devices/applications using bandwidth

**Solutions:**

- Try different quality settings
- Use download speed limiting to avoid detection
- Download during off-peak hours

**❓ Why do some downloads fail with "Unsupported URL"?**  
**Possible reasons:**

1. Platform not supported by yt-dlp
2. Regional restrictions on the content
3. Private/age-restricted content requiring cookies
4. Temporary server issues on the source platform

Check: The [yt-dlp supported sites list](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) for platform compatibility.

**❓ What if the app shows "Permission denied"?**  

- **On Linux/macOS:** Make sure the download path and temp folder are writable:  
  `chmod -R 755 ~/Videos`
- **On Windows:** Run the app as administrator

**❓ How do I clean up stuck temp files?**  
If the app closes unexpectedly, leftover .part files may remain. The app tries to remove them on exit, but you can safely delete them manually from the temp/ folder.

**❓ Where are logs stored?**  
You can find the latest session logs in the data/ folder. Include this file when reporting issues.

**❓ Can I use my own yt-dlp or FFmpeg binaries?**  
Yes. Place your custom builds inside the bin/ folder with the same names (yt-dlp, ffmpeg). The app automatically detects and uses them.

**❓ How do I use cookies for private videos?**  
In Settings, specify the path to your cookies.txt file or enable "Cookies from Browser." This enables downloading of age-restricted or private content.

**❓ I deleted desktop shortcut, how can I get it back?**  
**Quick Solution - Reset First Run:**  
Close the Video Downloader application completely

**Windows:**

- Right-click on `mt-vdl.exe`
- Select "Send to" → "Desktop (create shortcut)"
- **Or**
- Navigate to the application folder → `data/`
- Delete the file called `first_run.flag`
- Restart the application - it will prompt to create the desktop shortcut

**If not Windows OS:**

- Navigate to the application folder → `data/`
- Delete the file `./mediatools` (`rm ~/.mediatools`)
- Restart the application - it will prompt to create the desktop shortcut

---

## 🆘 Troubleshooting

**Common Issues and Solutions**

**❓ "yt-dlp not found" Error?**  
See "Installation & Setup" section above for complete solutions.

**❓ "FFmpeg not found" Error?**  
**Cause:** FFmpeg not installed or not accessible  
**Solution:**

1. Go to App → Settings → Reset to defaults, Restart App
2. Allow app to download FFmpeg, if it fails try step 3
3. Manually download FFmpeg if needed:
   - **Windows:** <https://www.gyan.dev/ffmpeg/builds/>
   - **Linux:** `sudo apt install ffmpeg`
   - **macOS:** `brew install ffmpeg`
4. Place in application's bin folder

**❓ Download Fails Immediately?**  
**Possible Causes:**

- Video no longer available
- Private video requiring authentication
- Unsupported platform

**Solution:**

1. Verify URL is correct and accessible in browser
2. Check if video requires login (use cookies)
3. Try updating yt-dlp
4. Check platform support

**❓ Slow Download Speeds?**  
**Possible Causes:**

- Internet connection speed
- Server-side throttling
- Download speed limit setting

**Solution:**

1. Check your internet speed
2. Increase speed limit in Settings
3. Try downloading at different times
4. Some platforms throttle during peak hours

**❓ Videos/Audio Download but Won't Play?**  
**Possible Causes:**

- Incomplete download
- Corrupted file
- Missing codecs in media player

**Solution:**

1. Check file size matches expected size
2. Re-download the media
3. Try different media player (VLC recommended for videos)
4. Update your media player codecs

**❓ Application Won't Start?**  
**Solution:**

1. Check system requirements
2. Run as administrator (Windows)
3. Check antivirus isn't blocking
4. Check if `bin/` folder has necessary executables
5. Reinstall the application
6. Delete application data folder to reset
7. Try running app from command window

**❓ Queue Not Persisting?**  
**Cause:** Multisession queue support disabled  
**Solution:**

1. Go to Settings → Queue Settings
2. Enable "Multisession Queue Download Support"
3. Queue will now save between sessions

**❓ Downloads stuck at 0% or very slow?**  
**Solutions:**

1. Check your internet connection
2. Try a different video URL to test
3. Restart the application

---

This FAQ applies to Video Downloader v2.1.0 and above. For the latest updates, check our [GitHub page](https://github.com/MediaTools-tech/mediatools).

If your issue isn't covered here, please check the [User Guide](docs/UserGuide.md) or open an issue on our [GitHub repository](https://github.com/MediaTools-tech/mediatools).

---

*FAQs maintained by Bala*
