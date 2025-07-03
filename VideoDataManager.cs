using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using System.Collections;

[Serializable]
public class VideoContent
{
    public int id;
    public string title;
    public string src;
    public string type;
    public string thumbnail;
    public float duration;
    public string category;
    public string show;
    public int episode;
    public string artist;
    public string part;
    public string song;
    public string director;
    public string film;
    public bool isTrailer;
}

[Serializable]
public class Channel
{
    public string id;
    public string name;
    public string description;
    public string currentShow;
    public string thumbnail;
    public List<VideoContent> content;
}

[Serializable]
public class Metadata
{
    public string version;
    public string lastUpdated;
    public int totalChannels;
    public int totalVideos;
}

[Serializable]
public class VideoData
{
    public List<Channel> channels;
    public Metadata metadata;
}

public class VideoDataManager : MonoBehaviour
{
    [Header("UI References")]
    public Transform thumbnailContainer;
    public GameObject thumbnailPrefab;
    public Transform channelContainer;
    public GameObject channelPrefab;
    
    [Header("Settings")]
    public string jsonUrl = "https://your-api-endpoint.com/video-data.json";
    public bool loadFromLocalFile = true;
    public TextAsset localJsonFile;
    
    private VideoData videoData;
    private Dictionary<string, Texture2D> thumbnailCache = new Dictionary<string, Texture2D>();
    
    void Start()
    {
        LoadVideoData();
    }
    
    public void LoadVideoData()
    {
        if (loadFromLocalFile && localJsonFile != null)
        {
            ParseVideoData(localJsonFile.text);
        }
        else
        {
            StartCoroutine(LoadVideoDataFromURL());
        }
    }
    
    private IEnumerator LoadVideoDataFromURL()
    {
        using (UnityWebRequest request = UnityWebRequest.Get(jsonUrl))
        {
            yield return request.SendWebRequest();
            
            if (request.result == UnityWebRequest.Result.Success)
            {
                ParseVideoData(request.downloadHandler.text);
            }
            else
            {
                Debug.LogError($"Failed to load video data: {request.error}");
            }
        }
    }
    
    private void ParseVideoData(string jsonText)
    {
        try
        {
            videoData = JsonUtility.FromJson<VideoData>(jsonText);
            Debug.Log($"Loaded {videoData.metadata.totalVideos} videos across {videoData.metadata.totalChannels} channels");
            
            // Populate UI
            PopulateChannels();
            PopulateThumbnails();
        }
        catch (Exception e)
        {
            Debug.LogError($"Failed to parse video data: {e.Message}");
        }
    }
    
    private void PopulateChannels()
    {
        if (channelContainer == null || channelPrefab == null) return;
        
        // Clear existing channels
        foreach (Transform child in channelContainer)
        {
            Destroy(child.gameObject);
        }
        
        // Create channel buttons
        foreach (Channel channel in videoData.channels)
        {
            GameObject channelObj = Instantiate(channelPrefab, channelContainer);
            ChannelButton channelButton = channelObj.GetComponent<ChannelButton>();
            
            if (channelButton != null)
            {
                channelButton.Initialize(channel);
                channelButton.OnChannelSelected += OnChannelSelected;
            }
        }
    }
    
    private void PopulateThumbnails(string channelId = null)
    {
        if (thumbnailContainer == null || thumbnailPrefab == null) return;
        
        // Clear existing thumbnails
        foreach (Transform child in thumbnailContainer)
        {
            Destroy(child.gameObject);
        }
        
        List<VideoContent> videosToShow = new List<VideoContent>();
        
        if (string.IsNullOrEmpty(channelId))
        {
            // Show all videos
            foreach (Channel channel in videoData.channels)
            {
                videosToShow.AddRange(channel.content);
            }
        }
        else
        {
            // Show videos from specific channel
            Channel selectedChannel = videoData.channels.Find(c => c.id == channelId);
            if (selectedChannel != null)
            {
                videosToShow.AddRange(selectedChannel.content);
            }
        }
        
        // Create thumbnail objects
        foreach (VideoContent video in videosToShow)
        {
            GameObject thumbnailObj = Instantiate(thumbnailPrefab, thumbnailContainer);
            ThumbnailButton thumbnailButton = thumbnailObj.GetComponent<ThumbnailButton>();
            
            if (thumbnailButton != null)
            {
                thumbnailButton.Initialize(video);
                thumbnailButton.OnVideoSelected += OnVideoSelected;
                
                // Load thumbnail image
                StartCoroutine(LoadThumbnail(video.thumbnail, thumbnailButton));
            }
        }
    }
    
    private IEnumerator LoadThumbnail(string thumbnailUrl, ThumbnailButton thumbnailButton)
    {
        // Check cache first
        if (thumbnailCache.ContainsKey(thumbnailUrl))
        {
            thumbnailButton.SetThumbnail(thumbnailCache[thumbnailUrl]);
            yield break;
        }
        
        using (UnityWebRequest request = UnityWebRequestTexture.GetTexture(thumbnailUrl))
        {
            yield return request.SendWebRequest();
            
            if (request.result == UnityWebRequest.Result.Success)
            {
                Texture2D texture = DownloadHandlerTexture.GetContent(request);
                thumbnailCache[thumbnailUrl] = texture;
                thumbnailButton.SetThumbnail(texture);
            }
            else
            {
                Debug.LogWarning($"Failed to load thumbnail: {thumbnailUrl}");
            }
        }
    }
    
    private void OnChannelSelected(Channel channel)
    {
        Debug.Log($"Selected channel: {channel.name}");
        PopulateThumbnails(channel.id);
    }
    
    private void OnVideoSelected(VideoContent video)
    {
        Debug.Log($"Selected video: {video.title}");
        // Handle video playback here
        PlayVideo(video);
    }
    
    private void PlayVideo(VideoContent video)
    {
        // Implement video playback logic
        // This could involve:
        // - Using Unity's VideoPlayer component
        // - Opening a web browser
        // - Streaming to a video player UI
        Debug.Log($"Playing video: {video.title} from {video.src}");
    }
    
    // Public methods for external access
    public List<Channel> GetAllChannels()
    {
        return videoData?.channels ?? new List<Channel>();
    }
    
    public List<VideoContent> GetAllVideos()
    {
        List<VideoContent> allVideos = new List<VideoContent>();
        if (videoData?.channels != null)
        {
            foreach (Channel channel in videoData.channels)
            {
                allVideos.AddRange(channel.content);
            }
        }
        return allVideos;
    }
    
    public List<VideoContent> GetVideosByCategory(string category)
    {
        List<VideoContent> categoryVideos = new List<VideoContent>();
        if (videoData?.channels != null)
        {
            foreach (Channel channel in videoData.channels)
            {
                foreach (VideoContent video in channel.content)
                {
                    if (video.category == category)
                    {
                        categoryVideos.Add(video);
                    }
                }
            }
        }
        return categoryVideos;
    }
    
    void OnDestroy()
    {
        // Clean up cached textures
        foreach (Texture2D texture in thumbnailCache.Values)
        {
            if (texture != null)
            {
                Destroy(texture);
            }
        }
        thumbnailCache.Clear();
    }
} 