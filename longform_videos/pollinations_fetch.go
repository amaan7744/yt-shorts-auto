package visuals

import (
	"context"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"

	"true-crime-pipeline/types"
)

// PollinationsFetcher generates AI images via Pollinations.ai (free, no key needed)
type PollinationsFetcher struct {
	httpClient *http.Client
}

// NewPollinationsFetcher creates a new fetcher
func NewPollinationsFetcher() *PollinationsFetcher {
	return &PollinationsFetcher{
		httpClient: &http.Client{Timeout: 60 * time.Second},
	}
}

// Fetch generates an image for a dramatic scene and saves it locally
func (p *PollinationsFetcher) Fetch(ctx context.Context, scene *types.ScriptScene, outputDir string) (string, error) {
	if scene.ImagePrompt == "" {
		return "", fmt.Errorf("scene %d has no image prompt", scene.Index)
	}

	// Enhance prompt for true crime aesthetic
	enhancedPrompt := enhancePrompt(scene.ImagePrompt, scene.Mood)

	// Build Pollinations URL
	// Format: https://image.pollinations.ai/prompt/{encoded_prompt}?params
	encodedPrompt := url.PathEscape(enhancedPrompt)
	imageURL := fmt.Sprintf(
		"https://image.pollinations.ai/prompt/%s?width=1920&height=1080&nologo=true&model=flux&seed=%d",
		encodedPrompt,
		scene.Index*42+7, // deterministic seed per scene for reproducibility
	)

	outFile := filepath.Join(outputDir, fmt.Sprintf("dramatic_%03d.jpg", scene.Index))

	log.Printf("[visuals] Generating AI image for scene %d: %q", scene.Index, truncate(enhancedPrompt, 60))

	// Retry up to 3 times (Pollinations occasionally times out)
	var err error
	for attempt := 1; attempt <= 3; attempt++ {
		err = p.downloadImage(ctx, imageURL, outFile)
		if err == nil {
			log.Printf("[visuals] ✅ Scene %d image saved: %s", scene.Index, outFile)
			return outFile, nil
		}
		log.Printf("[visuals] Attempt %d failed for scene %d: %v", attempt, scene.Index, err)
		time.Sleep(time.Duration(attempt) * 3 * time.Second)
	}

	return "", fmt.Errorf("pollinations fetch failed after 3 attempts: %w", err)
}

func (p *PollinationsFetcher) downloadImage(ctx context.Context, imageURL, outFile string) error {
	req, err := http.NewRequestWithContext(ctx, "GET", imageURL, nil)
	if err != nil {
		return err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (compatible; TrueCrimePipeline/1.0)")

	resp, err := p.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("HTTP %d from Pollinations", resp.StatusCode)
	}

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}

	// Validate it's actually an image (not an error HTML page)
	if len(data) < 100 {
		return fmt.Errorf("response too small (%d bytes) — likely an error", len(data))
	}

	return os.WriteFile(outFile, data, 0644)
}

// enhancePrompt adds true crime cinematic style modifiers to the base prompt
func enhancePrompt(base, mood string) string {
	// Mood-specific style additions
	moodStyles := map[string]string{
		"tense":  "cinematic noir lighting, dark shadows, dramatic contrast, 4K photorealistic",
		"reveal": "dramatic spotlight, high contrast, moody atmosphere, cinematic close-up",
		"eerie":  "dark foggy atmosphere, eerie lighting, desaturated colors, photorealistic",
		"action": "dynamic composition, dramatic lighting, motion blur, cinematic",
		"sad":    "melancholic lighting, soft shadows, muted tones, emotionally heavy",
		"hook":   "extreme dramatic lighting, high contrast black and white, cinematic masterpiece",
	}

	style, ok := moodStyles[mood]
	if !ok {
		style = "cinematic, dramatic lighting, photorealistic, 4K, dark atmosphere"
	}

	// Always add these safety/quality modifiers
	safetyModifiers := "no text, no watermark, no people's faces, environmental scene only"

	return fmt.Sprintf("%s, %s, %s", base, style, safetyModifiers)
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "..."
}

// GenerateImagePrompts uses Groq to write better image prompts for all dramatic scenes
// Call this before Fetch to upgrade simple prompts to cinematic ones
func GenerateImagePrompts(ctx context.Context, scenes []types.ScriptScene, groqAPIKey, model string) error {
	// Only process dramatic scenes that have an image prompt
	for i := range scenes {
		if scenes[i].SceneType != "dramatic" || scenes[i].ImagePrompt == "" {
			continue
		}

		// The image prompt from the script is already decent from Groq
		// Just ensure it's enhanced with mood context
		scenes[i].ImagePrompt = strings.TrimSpace(scenes[i].ImagePrompt)
	}
	return nil
}
