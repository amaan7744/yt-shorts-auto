package types

// Story holds a researched story ready for scripting
type Story struct {
	ID          string   `json:"id"`
	Title       string   `json:"title"`
	Body        string   `json:"body"`
	Source      string   `json:"source"`
	SourceURL   string   `json:"source_url"`
	Score       int      `json:"score"`
	PublishedAt string   `json:"published_at"`
	ImageURLs   []string `json:"image_urls"`
	Keywords    []string `json:"keywords"`
}

// ScriptScene is one scene/line in the script
type ScriptScene struct {
	Index             int     `json:"index"`
	TimestampStart    float64 `json:"timestamp_start"`
	TimestampEnd      float64 `json:"timestamp_end"`
	Narration         string  `json:"narration"`
	SceneType         string  `json:"scene_type"`  // cinematic | dramatic | proof
	Mood              string  `json:"mood"`         // tense | reveal | eerie | action | sad | hook
	ImagePrompt       string  `json:"image_prompt"`
	AssetTags         []string `json:"asset_tags"`
	ProofImageURL     string  `json:"proof_image_url"`
	ProofImageLocal   string  `json:"proof_image_local"`
	ProofDurationSec  float64 `json:"proof_duration_sec"`
	AudioFile         string  `json:"audio_file"`
	AudioDurationSec  float64 `json:"audio_duration_sec"`
	VisualFile        string  `json:"visual_file"`
	SFXFile           string  `json:"sfx_file"`
}

// Script is the full structured script for one video
type Script struct {
	StoryID     string        `json:"story_id"`
	Title       string        `json:"title"`
	TotalSec    float64       `json:"total_sec"`
	Scenes      []ScriptScene `json:"scenes"`
}

// VideoMetadata holds all YouTube upload metadata
type VideoMetadata struct {
	Title             string   `json:"title"`
	Description       string   `json:"description"`
	Tags              []string `json:"tags"`
	ThumbnailPrompt   string   `json:"thumbnail_prompt"`
	CategoryID        string   `json:"category_id"`
	Visibility        string   `json:"visibility"`
	ScheduledTimeUTC  string   `json:"scheduled_time_utc"`
}

// PipelineState tracks the full state of one pipeline run
type PipelineState struct {
	RunID         string        `json:"run_id"`
	StartedAt     string        `json:"started_at"`
	CompletedAt   string        `json:"completed_at"`
	Story         *Story        `json:"story"`
	Script        *Script       `json:"script"`
	AudioFile     string        `json:"audio_file"`
	VideoFile     string        `json:"video_file"`
	Metadata      *VideoMetadata `json:"metadata"`
	YouTubeURL    string        `json:"youtube_url"`
	YouTubeID     string        `json:"youtube_id"`
	Error         string        `json:"error,omitempty"`
}
