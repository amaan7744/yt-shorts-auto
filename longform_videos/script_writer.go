package script

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

const systemPrompt = `You are a professional true crime YouTube scriptwriter. You write gripping, cinematic scripts for faceless YouTube channels.

Your scripts MUST follow this exact structure:
1. COLD OPEN (0:00-0:30) - Start with the most shocking fact. No context. Hook immediately.
2. STORY BUILD (0:30-80%) - Chronological, escalating tension. Real details, real names, real places.
3. TWIST REVEAL (80%-95%) - The turn nobody saw coming. Let it land with weight.
4. OUTRO (95%-100%) - End with an open question to the viewer. Drive comments.

You MUST respond with ONLY valid JSON — no preamble, no markdown, no explanation.

Each scene in "scenes" array must have:
- "narration": the exact words to be spoken (1-4 sentences)
- "scene_type": one of "cinematic" | "dramatic" | "proof"
- "mood": one of "tense" | "reveal" | "eerie" | "action" | "sad" | "hook"
- "image_prompt": a detailed cinematic image generation prompt (for dramatic scenes) OR null
- "asset_tags": array of tags to match video clips (for cinematic scenes) OR null
- "proof_image_url": URL of real evidence image if available OR null
- "proof_duration_sec": how long to show proof image (3.0-6.0) OR null

Scene type rules:
- "cinematic" → uses asset video clips. Set asset_tags like ["dark","street","night","rain"]
- "dramatic" → uses AI generated image. Write a detailed image_prompt.
- "proof" → shows real evidence. Set proof_image_url if available.

Keep total narration to 5-10 minutes when read aloud at natural pace (~130 words per minute).`

// Writer generates scripts using Groq API
type Writer struct {
	cfg        *config.Config
	httpClient *http.Client
}

// New creates a new script Writer
func New(cfg *config.Config) *Writer {
	return &Writer{
		cfg:        cfg,
		httpClient: &http.Client{Timeout: 60 * time.Second},
	}
}

type groqRequest struct {
	Model       string        `json:"model"`
	Messages    []groqMessage `json:"messages"`
	Temperature float64       `json:"temperature"`
	MaxTokens   int           `json:"max_tokens"`
}

type groqMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type groqResponse struct {
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
	Error *struct {
		Message string `json:"message"`
	} `json:"error"`
}

// scriptJSON is the raw JSON structure returned by Groq
type scriptJSON struct {
	Title  string      `json:"title"`
	Scenes []sceneJSON `json:"scenes"`
}

type sceneJSON struct {
	Narration        string   `json:"narration"`
	SceneType        string   `json:"scene_type"`
	Mood             string   `json:"mood"`
	ImagePrompt      string   `json:"image_prompt"`
	AssetTags        []string `json:"asset_tags"`
	ProofImageURL    string   `json:"proof_image_url"`
	ProofDurationSec float64  `json:"proof_duration_sec"`
}

// Run generates a full script from a story
func (w *Writer) Run(ctx context.Context, story *types.Story) (*types.Script, error) {
	log.Println("[script] Generating script via Groq (Llama 3)...")

	apiKey := os.Getenv("GROQ_API_KEY")
	if apiKey == "" {
		return nil, fmt.Errorf("GROQ_API_KEY not set")
	}

	userPrompt := buildUserPrompt(story, w.cfg.Script.TargetDurationMin, w.cfg.Script.TargetDurationMax)

	reqBody := groqRequest{
		Model: w.cfg.Script.GroqModel,
		Messages: []groqMessage{
			{Role: "system", Content: systemPrompt},
			{Role: "user", Content: userPrompt},
		},
		Temperature: w.cfg.Script.Temperature,
		MaxTokens:   4096,
	}

	bodyBytes, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", "https://api.groq.com/openai/v1/chat/completions", bytes.NewReader(bodyBytes))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := w.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("groq request: %w", err)
	}
	defer resp.Body.Close()

	respBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var groqResp groqResponse
	if err := json.Unmarshal(respBytes, &groqResp); err != nil {
		return nil, fmt.Errorf("parse groq response: %w", err)
	}

	if groqResp.Error != nil {
		return nil, fmt.Errorf("groq error: %s", groqResp.Error.Message)
	}

	if len(groqResp.Choices) == 0 {
		return nil, fmt.Errorf("groq returned no choices")
	}

	content := groqResp.Choices[0].Message.Content
	content = cleanJSON(content)

	var raw scriptJSON
	if err := json.Unmarshal([]byte(content), &raw); err != nil {
		return nil, fmt.Errorf("parse script JSON: %w\nraw content: %s", err, content[:min(200, len(content))])
	}

	script := convertToScript(story.ID, raw)
	log.Printf("[script] ✅ Script ready: %d scenes, ~%.0f seconds", len(script.Scenes), script.TotalSec)
	return script, nil
}

func buildUserPrompt(story *types.Story, minMin, maxMin int) string {
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Write a %d-%d minute true crime YouTube script about the following story.\n\n", minMin, maxMin))
	sb.WriteString(fmt.Sprintf("STORY TITLE: %s\n\n", story.Title))
	sb.WriteString(fmt.Sprintf("SOURCE: %s (%s)\n\n", story.Source, story.SourceURL))
	sb.WriteString(fmt.Sprintf("STORY CONTENT:\n%s\n\n", story.Body))

	if len(story.ImageURLs) > 0 {
		sb.WriteString("AVAILABLE PROOF IMAGES (use as proof_image_url in relevant scenes):\n")
		for _, u := range story.ImageURLs {
			sb.WriteString("- " + u + "\n")
		}
		sb.WriteString("\n")
	}

	sb.WriteString("Respond ONLY with valid JSON. No markdown. No explanation.")
	return sb.String()
}

func convertToScript(storyID string, raw scriptJSON) *types.Script {
	script := &types.Script{
		StoryID: storyID,
		Title:   raw.Title,
	}

	// Estimate timing: ~130 words per minute
	var elapsed float64
	for i, s := range raw.Scenes {
		wordCount := len(strings.Fields(s.Narration))
		duration := float64(wordCount) / 130.0 * 60.0 // seconds

		scene := types.ScriptScene{
			Index:            i,
			TimestampStart:   elapsed,
			TimestampEnd:     elapsed + duration,
			Narration:        s.Narration,
			SceneType:        s.SceneType,
			Mood:             s.Mood,
			ImagePrompt:      s.ImagePrompt,
			AssetTags:        s.AssetTags,
			ProofImageURL:    s.ProofImageURL,
			ProofDurationSec: s.ProofDurationSec,
			AudioDurationSec: duration,
		}

		// Default proof duration
		if scene.SceneType == "proof" && scene.ProofDurationSec == 0 {
			scene.ProofDurationSec = 4.0
		}

		elapsed += duration
		script.Scenes = append(script.Scenes, scene)
	}

	script.TotalSec = elapsed
	return script
}

// cleanJSON strips markdown fences if Groq wraps response in ```json ... ```
func cleanJSON(s string) string {
	s = strings.TrimSpace(s)
	s = strings.TrimPrefix(s, "```json")
	s = strings.TrimPrefix(s, "```")
	s = strings.TrimSuffix(s, "```")
	return strings.TrimSpace(s)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
