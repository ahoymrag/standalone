using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using System;

public class ThumbnailButton : MonoBehaviour, IPointerClickHandler
{
    [Header("UI References")]
    public Image thumbnailImage;
    public Text titleText;
    public Text categoryText;
    public Text durationText;
    public GameObject playButton;
    public GameObject loadingIndicator;
    
    [Header("Settings")]
    public Color normalColor = Color.white;
    public Color hoverColor = new Color(0.9f, 0.9f, 0.9f, 1f);
    public Color selectedColor = new Color(0.8f, 0.8f, 1f, 1f);
    
    private VideoContent videoData;
    private bool isSelected = false;
    
    public event Action<VideoContent> OnVideoSelected;
    
    void Awake()
    {
        // Auto-assign UI components if not set
        if (thumbnailImage == null)
            thumbnailImage = GetComponentInChildren<Image>();
        
        if (titleText == null)
            titleText = GetComponentInChildren<Text>();
    }
    
    public void Initialize(VideoContent video)
    {
        videoData = video;
        UpdateUI();
    }
    
    private void UpdateUI()
    {
        if (videoData == null) return;
        
        // Set title
        if (titleText != null)
        {
            titleText.text = videoData.title;
        }
        
        // Set category
        if (categoryText != null)
        {
            categoryText.text = GetCategoryDisplayName(videoData.category);
        }
        
        // Set duration
        if (durationText != null)
        {
            durationText.text = FormatDuration(videoData.duration);
        }
        
        // Show loading indicator initially
        if (loadingIndicator != null)
        {
            loadingIndicator.SetActive(true);
        }
        
        // Hide play button until thumbnail is loaded
        if (playButton != null)
        {
            playButton.SetActive(false);
        }
    }
    
    public void SetThumbnail(Texture2D texture)
    {
        if (thumbnailImage != null && texture != null)
        {
            // Convert Texture2D to Sprite
            Sprite sprite = Sprite.Create(texture, new Rect(0, 0, texture.width, texture.height), new Vector2(0.5f, 0.5f));
            thumbnailImage.sprite = sprite;
            
            // Hide loading indicator
            if (loadingIndicator != null)
            {
                loadingIndicator.SetActive(false);
            }
            
            // Show play button
            if (playButton != null)
            {
                playButton.SetActive(true);
            }
        }
    }
    
    public void OnPointerClick(PointerEventData eventData)
    {
        if (videoData != null)
        {
            OnVideoSelected?.Invoke(videoData);
        }
    }
    
    public void SetSelected(bool selected)
    {
        isSelected = selected;
        UpdateVisualState();
    }
    
    private void UpdateVisualState()
    {
        if (thumbnailImage != null)
        {
            thumbnailImage.color = isSelected ? selectedColor : normalColor;
        }
    }
    
    private string GetCategoryDisplayName(string category)
    {
        switch (category?.ToLower())
        {
            case "episodes":
                return "Episode";
            case "clips":
                return "Clip";
            case "music":
                return "Music Video";
            case "shorts":
                return "Short Film";
            default:
                return category ?? "Unknown";
        }
    }
    
    private string FormatDuration(float duration)
    {
        if (duration <= 0) return "";
        
        int minutes = Mathf.FloorToInt(duration / 60f);
        int seconds = Mathf.FloorToInt(duration % 60f);
        return $"{minutes}:{seconds:D2}";
    }
    
    // Public getters
    public VideoContent GetVideoData()
    {
        return videoData;
    }
    
    public bool IsSelected()
    {
        return isSelected;
    }
} 