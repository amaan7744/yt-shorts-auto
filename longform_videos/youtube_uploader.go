package upload

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	"true-crime-pipeline/config"
	"true-crime-pipeline/types"

	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
	"google.golang.org/api/option"
	"google.golang.org/api/youtube/v3"
)

// Uploader handles YouTube video upload via Data API v3
type Uploader struct {
	cfg *config.Config
}

// New creates a new Uploader
func New(cfg *config.Config) *Uploader {
	return &Uploader{cfg: cfg}
}

// Run uploads the final video to YouTube with all metadata
func (u *Uploader) Run(ctx context.Context, videoFile string, metadata *types.VideoMetadata) (string, string, error) {
	log.Println("[upload] Authenticating with YouTube API...")

	client, err := u.getOAuthClient(ctx)
	if err != nil {
		return "", "", fmt.Errorf("youtube auth: %w", err)
	}

	svc, err := youtube.NewService(ctx, option.WithHTTPClient(client))
	if err != nil {
		return "", "", fmt.Errorf("youtube service: %w", err)
	}

	log.Printf("[upload] Uploading: %q", metadata.Title)

	// Build video snippet
	snippet := &youtube.VideoSnippet{
		Title:                metadata.Title,
		Description:          metadata.Description,
		Tags:                 metadata.Tags,
		CategoryId:           metadata.CategoryID,
		DefaultLanguage:      u.cfg.Upload.DefaultLanguage,
		DefaultAudioLanguage: u.cfg.Upload.DefaultLanguage,
	}

	// Build video status
	status := &youtube.VideoStatus{
		PrivacyStatus:           metadata.Visibility,
		SelfDeclaredMadeForKids: u.cfg.Upload.MadeForKids,
		NotifySubscribers:       u.cfg.Upload.NotifySubscribers,
	}

	// Schedule publish time if provided
	if metadata.ScheduledTimeUTC != "" && metadata.Visibility == "public" {
		status.PrivacyStatus = "private" // must be private to schedule
		status.PublishAt = metadata.ScheduledTimeUTC
		log.Printf("[upload] Scheduled for: %s UTC", metadata.ScheduledTimeUTC)
	}

	video := &youtube.Video{
		Snippet: snippet,
		Status:  status,
	}

	// Open video file
	f, err := os.Open(videoFile)
	if err != nil {
		return "", "", fmt.Errorf("open video file: %w", err)
	}
	defer f.Close()

	// Get file size for progress tracking
	fi, _ := f.Stat()
	log.Printf("[upload] File size: %.1f MB", float64(fi.Size())/1024/1024)

	// Upload with resumable upload (required for files > 5MB)
	call := svc.Videos.Insert([]string{"snippet", "status"}, video)
	call.Media(f)

	uploadedVideo, err := call.Do()
	if err != nil {
		return "", "", fmt.Errorf("youtube upload: %w", err)
	}

	videoID := uploadedVideo.Id
	videoURL := fmt.Sprintf("https://www.youtube.com/watch?v=%s", videoID)

	log.Printf("[upload] ✅ Uploaded successfully!")
	log.Printf("[upload] Video ID: %s", videoID)
	log.Printf("[upload] Video URL: %s", videoURL)

	return videoID, videoURL, nil
}

// getOAuthClient creates an OAuth2 HTTP client using env credentials
func (u *Uploader) getOAuthClient(ctx context.Context) (*oauth2.Transport, error) {
	clientID := os.Getenv("YOUTUBE_CLIENT_ID")
	clientSecret := os.Getenv("YOUTUBE_CLIENT_SECRET")
	refreshToken := os.Getenv("YOUTUBE_REFRESH_TOKEN")

	if clientID == "" || clientSecret == "" || refreshToken == "" {
		return nil, fmt.Errorf("YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, or YOUTUBE_REFRESH_TOKEN not set")
	}

	conf := &oauth2.Config{
		ClientID:     clientID,
		ClientSecret: clientSecret,
		Endpoint:     google.Endpoint,
		Scopes:       []string{youtube.YoutubeUploadScope, youtube.YoutubeScope},
	}

	token := &oauth2.Token{
		RefreshToken: refreshToken,
		Expiry:       time.Now().Add(-time.Hour), // force refresh
	}

	tokenSource := conf.TokenSource(ctx, token)
	transport := &oauth2.Transport{
		Source: tokenSource,
		Base:   nil,
	}

	return transport, nil
}

// LogUpload saves the upload result to the logs directory
func LogUpload(videoID, videoURL, videoFile, outputDir string, metadata *types.VideoMetadata) error {
	logEntry := map[string]interface{}{
		"video_id":      videoID,
		"video_url":     videoURL,
		"title":         metadata.Title,
		"scheduled_utc": metadata.ScheduledTimeUTC,
		"uploaded_at":   time.Now().UTC().Format(time.RFC3339),
		"video_file":    videoFile,
	}

	logFile := fmt.Sprintf("%s/upload_%s.json", outputDir, time.Now().Format("20060102_150405"))
	data, _ := json.MarshalIndent(logEntry, "", "  ")
	if err := os.WriteFile(logFile, data, 0644); err != nil {
		return err
	}

	log.Printf("[upload] Upload log saved: %s", logFile)
	return nil
}
