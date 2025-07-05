from django.shortcuts import render, HttpResponse
import re
# Import yt_dlp instead of youtube_dl
import yt_dlp as youtube_dl 
from .forms import DownloadForm # Assuming DownloadForm is defined in forms.py

def download_video(request):
    form = DownloadForm(request.POST or None)
    context = {} # Initialize context here to ensure it's always defined

    if request.method == 'POST' and form.is_valid():
        video_url = form.cleaned_data.get("url")
        # Basic regex for YouTube URLs
        regex = r'^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$'
        if not re.match(regex, video_url):
            return HttpResponse('Enter a correct YouTube URL.')

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best', # Prioritize best combined video and audio
            'noplaylist': True, # Do not download playlists, only single videos
            'quiet': True, # Suppress console output from yt-dlp
            'no_warnings': True, # Suppress warnings from yt-dlp
            'simulate': True, # Do not actually download, just extract info
            'retries': 5, # Number of retries for network errors
            'force_ipv4': True, # Force IPv4 to avoid potential IPv6 issues
            # Add a common user-agent to mimic a browser
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            # Add a referer header
            'referer': 'https://www.youtube.com/',
            # Bypass geographic restrictions by faking a country code (e.g., 'US')
            # This can sometimes help with access issues, though not directly for bot detection
            'geo_bypass_country': 'US', 
        }
        
        try:
            # Use yt_dlp (aliased as youtube_dl) to extract information
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                # extract_info will fetch video metadata without downloading
                meta = ydl.extract_info(video_url, download=False)
            
            # Prepare streams for display
            video_audio_streams = []
            # Iterate through formats to get available resolutions and formats
            for m in meta.get('formats', []):
                # Ensure format has a URL and is not an advertisement or broken stream
                if m.get('url') and m.get('vcodec') != 'none' and m.get('acodec') != 'none':
                    file_size = m.get('filesize')
                    if file_size is not None:
                        file_size = f'{round(int(file_size) / (1024 * 1024), 2)} MB' # Convert bytes to MB
                    else:
                        file_size = 'N/A' # If filesize is not available

                    resolution = 'Audio Only' # Default for audio streams
                    if m.get('height') is not None and m.get('width') is not None:
                        resolution = f"{m['height']}x{m['width']}"
                    
                    video_audio_streams.append({
                        'resolution': resolution,
                        'extension': m.get('ext', 'N/A'),
                        'file_size': file_size,
                        'video_url': m['url']
                    })
            
            # Sort streams by resolution (descending) or file size if resolution is same
            video_audio_streams.sort(key=lambda x: (
                int(x['resolution'].split('x')[0]) if 'x' in x['resolution'] else 0,
                float(x['file_size'].replace(' MB', '')) if 'MB' in str(x['file_size']) else 0
            ), reverse=True)

            context = {
                'form': form,
                'title': meta.get('title', 'N/A'),
                'streams': video_audio_streams,
                'description': meta.get('description', 'No description available.'),
                'likes': f'{int(meta.get("like_count", 0)):,}' if meta.get("like_count") is not None else 'N/A',
                'dislikes': f'{int(meta.get("dislike_count", 0)):,}' if meta.get("dislike_count") is not None else 'N/A',
                'thumb': meta.get('thumbnails', [{}])[3].get('url') if len(meta.get('thumbnails', [])) > 3 else (meta.get('thumbnails', [{}])[0].get('url') if len(meta.get('thumbnails', [])) > 0 else 'https://placehold.co/480x360/cccccc/333333?text=No+Thumbnail'), # Fallback to first thumbnail or placeholder
                'duration': round(int(meta.get('duration', 0))/60, 2) if meta.get('duration') is not None else 'N/A',
                'views': f'{int(meta.get("view_count", 0)):,}' if meta.get("view_count") is not None else 'N/A'
            }
            return render(request, 'home.html', context)
        except Exception as error:
            # Safely encode the error message for printing to console/logs
            safe_error_for_print = str(error).encode('ascii', 'xmlcharrefreplace').decode('ascii')
            print(f"Error during video info extraction: {safe_error_for_print}") # Log the full error for debugging

            # Check for specific yt-dlp authentication error
            error_message_str = str(error)
            if "Sign in to confirm you’re not a bot" in error_message_str or "Use --cookies-from-browser or --cookies for the authentication" in error_message_str:
                user_friendly_message = "This video requires authentication or is restricted. Our public downloader cannot access it. Please try a different video."
            else:
                user_friendly_message = "Could not extract video information. Please check the URL or try again later."
            
            # Safely encode the user-friendly message for HttpResponse
            error_message_for_http = str(user_friendly_message).encode('ascii', 'xmlcharrefreplace').decode('ascii')
            return HttpResponse(f'An error occurred: {error_message_for_http}')
    
    # If it's a GET request or form is not valid
    return render(request, 'home.html', {'form': form})
