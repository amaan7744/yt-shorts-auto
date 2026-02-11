package config

import (
	"os"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Research  ResearchConfig  `yaml:"research"`
	Script    ScriptConfig    `yaml:"script"`
	Audio     AudioConfig     `yaml:"audio"`
	Visuals   VisualsConfig   `yaml:"visuals"`
	Assets    AssetsConfig    `yaml:"assets"`
	Subtitles SubtitlesConfig `yaml:"subtitles"`
	SFX       SFXConfig       `yaml:"sfx"`
	Metadata  MetadataConfig  `yaml:"metadata"`
	Upload    UploadConfig    `yaml:"upload"`
	Schedule  ScheduleConfig  `yaml:"schedule"`
	Paths     PathsConfig     `yaml:"paths"`
}

type ResearchConfig struct {
	Subreddits         []string `yaml:"subreddits"`
	NewsKeywords       []string `yaml:"news_keywords"`
	StoryLookbackDays  int      `yaml:"story_lookback_days"`
	MinRedditScore     int      `yaml:"min_reddit_score"`
	MinComments        int      `yaml:"min_comments"`
	MaxStoriesToEval   int      `yaml:"max_stories_to_evaluate"`
}

type ScriptConfig struct {
	TargetDurationMin int     `yaml:"target_duration_min"`
	TargetDurationMax int     `yaml:"target_duration_max"`
	Structure         string  `yaml:"structure"`
	GroqModel         string  `yaml:"groq_model"`
	Temperature       float64 `yaml:"temperature"`
}

type AudioConfig struct {
	OutputFormat string `yaml:"output_format"`
	SampleRate   int    `yaml:"sample_rate"`
}

type VisualsConfig struct {
	VideoResolution          string  `yaml:"video_resolution"`
	FPS                      int     `yaml:"fps"`
	ProofAspectRatio         string  `yaml:"proof_aspect_ratio"`
	ProofPosition            string  `yaml:"proof_position"`
	ProofSlideDirection      string  `yaml:"proof_slide_direction"`
	ProofAnimationDurationSec float64 `yaml:"proof_animation_duration_sec"`
	ProofHoldSecDefault      float64 `yaml:"proof_hold_sec_default"`
	BackgroundDimDuringProof float64 `yaml:"background_dim_during_proof"`
	ProofCornerRadius        int     `yaml:"proof_corner_radius"`
	ProofShadow              bool    `yaml:"proof_shadow"`
	KenBurnsZoomFactor       float64 `yaml:"ken_burns_zoom_factor"`
}

type AssetsConfig struct {
	NeverRepeatInSameVideo bool    `yaml:"never_repeat_in_same_video"`
	ClipTrimMode           string  `yaml:"clip_trim_mode"`
	LoopCrossfadeSec       float64 `yaml:"loop_crossfade_sec"`
	FallbackIfNoMatch      string  `yaml:"fallback_if_no_match"`
}

type SubtitlesConfig struct {
	Engine        string `yaml:"engine"`
	WhisperModel  string `yaml:"whisper_model"`
	BurnIntoVideo bool   `yaml:"burn_into_video"`
	Font          string `yaml:"font"`
	FontSize      int    `yaml:"font_size"`
	FontWeight    string `yaml:"font_weight"`
	Color         string `yaml:"color"`
	StrokeColor   string `yaml:"stroke_color"`
	StrokeWidth   float64 `yaml:"stroke_width"`
	Position      string `yaml:"position"`
	MarginBottom  int    `yaml:"margin_bottom"`
	MaxCharsPerLine int  `yaml:"max_chars_per_line"`
}

type SFXConfig struct {
	Enabled               bool               `yaml:"enabled"`
	VolumeUnderNarration  float64            `yaml:"volume_under_narration"`
	FadeInSec             float64            `yaml:"fade_in_sec"`
	FadeOutSec            float64            `yaml:"fade_out_sec"`
	MoodToSFXMap          map[string]string  `yaml:"mood_to_sfx_map"`
}

type MetadataConfig struct {
	GroqModel               string `yaml:"groq_model"`
	TitleMaxChars           int    `yaml:"title_max_chars"`
	DescriptionWordCount    int    `yaml:"description_word_count"`
	TagsCount               int    `yaml:"tags_count"`
	YouTubeCategoryID       string `yaml:"youtube_category_id"`
	GenerateThumbnailPrompt bool   `yaml:"generate_thumbnail_prompt"`
}

type UploadConfig struct {
	Visibility        string `yaml:"visibility"`
	ScheduleTimeEST   string `yaml:"schedule_time_est"`
	NotifySubscribers bool   `yaml:"notify_subscribers"`
	MadeForKids       bool   `yaml:"made_for_kids"`
	DefaultLanguage   string `yaml:"default_language"`
}

type ScheduleConfig struct {
	TuesdayCron string `yaml:"tuesday_cron"`
	FridayCron  string `yaml:"friday_cron"`
}

type PathsConfig struct {
	AssetsVideo    string `yaml:"assets_video"`
	AssetsSFX      string `yaml:"assets_sfx"`
	VideoTags      string `yaml:"video_tags"`
	SFXTags        string `yaml:"sfx_tags"`
	ClipUsageLog   string `yaml:"clip_usage_log"`
	UsedStoriesLog string `yaml:"used_stories_log"`
	Output         string `yaml:"output"`
	Logs           string `yaml:"logs"`
}

// Load reads config.yaml and returns a Config struct
func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
}
