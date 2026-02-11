package metadata

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"true-crime-pipeline/config"
	"true-crime-pipeline/types"
)

const metadataSystemPrompt = `You are an expert YouTube SEO strategist and true crime content specialist.
Generate compelling YouTube metadata that maximizes click-through rate and search ranking.

You MUST respond with ONLY valid JSON — no markdown, no explanation, no preamble.

The JSON must have exactly these fields:
- "title": string (max 70 chars, must be click-bait but honest, true crime hook style)
- "description": string (~500 words, SEO-rich, includes timestamps placeholder, source credits, channel CTA)
- "tags": array of 30 strings (mix of broad and specific tags)
- "thumbnail_prompt": string (detailed prompt for a dramatic thumbnail image)

Title formulas that work for true crime:
- "She [did X]. Nobody Knew [shocking fact]."
- "The [Person] Who [shocking action]. The Truth Will Disturb You."  
- "[Number] Days. [Number] Victims. Nobody Suspected [person]."
- "He Was A [trusted role]. Then They Found [evidence]."
- "The [Case] That Still Has No Answers."

Thumbnail prompt should describe: dramatic face/scene, high contrast, dark tones, text overlay area, eye-catching.`

// Generator creates YouTube metadata via Groq
type Generator struct {
	cfg        *config.Config
	httpClient *http.Client
}

// New creates a new metadata Generator
func New(cfg *config.Config) *Generator {
	return &Generator{
		cfg:        cfg,
		httpClient: &http.Client{Timeout: 30 * time.Second},
	}
}

type metadataJSON struct {
	Title           string   `json:"title"`
	Description     string   `json:"description"`
	Tags            []string `json:"tags"`
	ThumbnailPrompt string   `json:"thumbnail_prompt"`
}

// Run generates all YouTube metadata for the video
func (g *Generator) Run(ctx context.Context, script *types.Script, story *types.Story) (*types.VideoMetadata, error) {
	log.Println("[metadata] Generating YouTube metadata via Groq...")

	apiKey := os.Getenv("GROQ_API_KEY")
	if apiKey == "" {
		return nil, fmt.Errorf("GROQ_API_KEY not set")
	}

	userPrompt := buildMetadataPrompt(script, story, g.cfg)

	reqBody := map[string]interface{}{
		"model": g.cfg.Metadata.GroqModel,
		"messages": []map[string]string{
			{"role": "system", "content": metadataSystemPrompt},
			{"role": "user", "content": userPrompt},
		},
		"temperature": 0.8,
		"max_tokens":  2048,
	}

	bodyBytes, _ := json.Marshal(reqBody)
	req, err := http.NewRequestWithContext(ctx, "POST",
		"https://api.groq.com/openai/v1/chat/completions",
		bytes.NewReader(bodyBytes),
	)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := g.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("groq request: %w", err)
	}
	defer resp.Body.Close()

	respBytes, _ := io.ReadAll(resp.Body)

	var groqResp struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
		Error *struct {
			Message string `json:"message"`
		} `json:"error"`
	}

	if err := json.Unmarshal(respBytes, &groqResp); err != nil {
		return nil, fmt.Errorf("parse groq response: %w", err)
	}
	if groqResp.Error != nil {
		return nil, fmt.Errorf("groq error: %s", groqResp.Error.Message)
	}
	if len(groqResp.Choices) == 0 {
		return nil, fmt.Errorf("groq returned no choices")
	}

	content := cleanJSON(groqResp.Choices[0].Message.Content)

	var raw metadataJSON
	if err := json.Unmarshal([]byte(content), &raw); err != nil {
		return nil, fmt.Errorf("parse metadata JSON: %w\ncontent: %s", err, content[:min(300, len(content))])
	}

	// Enforce title length
	title := raw.Title
	if len(title) > g.cfg.Metadata.TitleMaxChars {
		title = title[:g.cfg.Metadata.TitleMaxChars-3] + "..."
	}

	// Calculate scheduled upload time (2PM EST on next Tue or Fri)
	scheduledTime := nextUploadTime()

	metadata := &types.VideoMetadata{
		Title:            title,
		Description:      raw.Description,
		Tags:             raw.Tags[:min(30, len(raw.Tags))],
		ThumbnailPrompt:  raw.ThumbnailPrompt,
		CategoryID:       g.cfg.Metadata.YouTubeCategoryID,
		Visibility:       g.cfg.Upload.Visibility,
		ScheduledTimeUTC: scheduledTime,
	}

	log.Printf("[metadata] ✅ Title: %q", metadata.Title)
	log.Printf("[metadata] Tags: %d generated", len(metadata.Tags))
	return metadata, nil
}

func buildMetadataPrompt(script *types.Script, story *types.Story, cfg *config.Config) string {
	var sb strings.Builder
	sb.WriteString("Generate YouTube metadata for this true crime video.\n\n")
	sb.WriteString(fmt.Sprintf("VIDEO TITLE (working): %s\n\n", script.Title))
	sb.WriteString(fmt.Sprintf("STORY SOURCE: %s\n", story.Source))
	sb.WriteString(fmt.Sprintf("STORY URL: %s\n\n", story.SourceURL))
	sb.WriteString(fmt.Sprintf("TOTAL VIDEO DURATION: %.0f seconds (~%.1f minutes)\n\n", script.TotalSec, script.TotalSec/60))

	sb.WriteString("SCRIPT SUMMARY (first 3 and last 2 scenes):\n")
	scenes := script.Scenes
	preview := scenes
	if len(scenes) > 5 {
		preview = append(scenes[:3], scenes[len(scenes)-2:]...)
	}
	for _, s := range preview {
		sb.WriteString(fmt.Sprintf("- [%s/%s] %s\n", s.SceneType, s.Mood, truncate(s.Narration, 100)))
	}

	sb.WriteString("\nDescription should include:\n")
	sb.WriteString("- Hook paragraph (2 sentences)\n")
	sb.WriteString("- What the video covers (3-4 sentences)\n")
	sb.WriteString("- Timestamps section: 0:00 Introduction, etc.\n")
	sb.WriteString(fmt.Sprintf("- Source credit: %s\n", story.Source))
	sb.WriteString("- Subscribe CTA\n")
	sb.WriteString("- Comment question to drive engagement\n\n")
	sb.WriteString("Respond ONLY with valid JSON.")
	return sb.String()
}

// nextUploadTime returns the next Tuesday or Friday at 2PM EST in UTC
func nextUploadTime() string {
	loc, _ := time.LoadLocation("America/New_York")
	now := time.Now().In(loc)

	// Find next Tuesday (2) or Friday (5)
	for i := 1; i <= 7; i++ {
		candidate := now.AddDate(0, 0, i)
		wd := candidate.Weekday()
		if wd == time.Tuesday || wd == time.Friday {
			upload := time.Date(candidate.Year(), candidate.Month(), candidate.Day(),
				14, 0, 0, 0, loc) // 2PM EST
			return upload.UTC().Format(time.RFC3339)
		}
	}
	return time.Now().UTC().Add(48 * time.Hour).Format(time.RFC3339)
}

func cleanJSON(s string) string {
	s = strings.TrimSpace(s)
	s = strings.TrimPrefix(s, "```json")
	s = strings.TrimPrefix(s, "```")
	s = strings.TrimSuffix(s, "```")
	return strings.TrimSpace(s)
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "..."
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
