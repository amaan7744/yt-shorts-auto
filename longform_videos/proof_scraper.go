package visuals

import (
	"context"
	"encoding/json"
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

// ProofScraper fetches real evidence images for proof scenes
type ProofScraper struct {
	httpClient *http.Client
	serpAPIKey string
}

// NewProofScraper creates a new ProofScraper
func NewProofScraper() *ProofScraper {
	return &ProofScraper{
		httpClient: &http.Client{Timeout: 20 * time.Second},
		serpAPIKey: os.Getenv("SERPAPI_KEY"),
	}
}

// FetchProofImage downloads a proof image for a scene
// It tries the scene's existing URL first, then falls back to scraping
func (ps *ProofScraper) FetchProofImage(ctx context.Context, scene *types.ScriptScene, story *types.Story, outputDir string) (string, error) {
	outFile := filepath.Join(outputDir, fmt.Sprintf("proof_%03d.jpg", scene.Index))

	// Try scene's existing proof URL first
	if scene.ProofImageURL != "" {
		log.Printf("[proof] Scene %d: downloading from URL: %s", scene.Index, truncate(scene.ProofImageURL, 60))
		if err := ps.downloadFile(ctx, scene.ProofImageURL, outFile); err == nil {
			return outFile, nil
		}
		log.Printf("[proof] Scene %d: URL download failed, trying Wikipedia fallback", scene.Index)
	}

	// Try Wikipedia for images of people/places mentioned
	if img, err := ps.searchWikipedia(ctx, scene.Narration, outputDir, scene.Index); err == nil {
		return img, nil
	}

	// Try story's existing image URLs
	for _, imgURL := range story.ImageURLs {
		if err := ps.downloadFile(ctx, imgURL, outFile); err == nil {
			log.Printf("[proof] Scene %d: using story image: %s", scene.Index, truncate(imgURL, 60))
			return outFile, nil
		}
	}

	// Try SerpAPI Google Images as last resort
	if ps.serpAPIKey != "" {
		if img, err := ps.searchGoogleImages(ctx, scene.Narration, story.Title, outputDir, scene.Index); err == nil {
			return img, nil
		}
	}

	return "", fmt.Errorf("no proof image found for scene %d", scene.Index)
}

// searchWikipedia searches Wikipedia for an image related to the narration text
func (ps *ProofScraper) searchWikipedia(ctx context.Context, narration, outputDir string, sceneIndex int) (string, error) {
	// Extract key terms from narration for Wikipedia search
	query := extractSearchQuery(narration)
	if query == "" {
		return "", fmt.Errorf("no query extracted")
	}

	// Wikipedia API search
	searchURL := fmt.Sprintf(
		"https://en.wikipedia.org/api/rest_v1/page/summary/%s",
		url.PathEscape(query),
	)

	req, _ := http.NewRequestWithContext(ctx, "GET", searchURL, nil)
	req.Header.Set("User-Agent", "TrueCrimePipeline/1.0 (educational)")
	resp, err := ps.httpClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return "", fmt.Errorf("wikipedia returned %d", resp.StatusCode)
	}

	var result struct {
		Thumbnail struct {
			Source string `json:"source"`
		} `json:"thumbnail"`
		OriginalImage struct {
			Source string `json:"source"`
		} `json:"originalimage"`
		Title string `json:"title"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}

	imgURL := result.OriginalImage.Source
	if imgURL == "" {
		imgURL = result.Thumbnail.Source
	}
	if imgURL == "" {
		return "", fmt.Errorf("no image in Wikipedia result for %q", query)
	}

	outFile := filepath.Join(outputDir, fmt.Sprintf("proof_%03d_wiki.jpg", sceneIndex))
	if err := ps.downloadFile(ctx, imgURL, outFile); err != nil {
		return "", err
	}

	log.Printf("[proof] Scene %d: Wikipedia image found for %q", sceneIndex, query)
	return outFile, nil
}

// searchGoogleImages uses SerpAPI to find relevant Google Images
func (ps *ProofScraper) searchGoogleImages(ctx context.Context, narration, storyTitle, outputDir string, sceneIndex int) (string, error) {
	query := storyTitle + " " + extractSearchQuery(narration)

	serpURL := fmt.Sprintf(
		"https://serpapi.com/search.json?engine=google_images&q=%s&num=3&api_key=%s",
		url.QueryEscape(query),
		ps.serpAPIKey,
	)

	req, _ := http.NewRequestWithContext(ctx, "GET", serpURL, nil)
	resp, err := ps.httpClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var result struct {
		ImagesResults []struct {
			Original string `json:"original"`
			Source   string `json:"source"`
		} `json:"images_results"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}

	if len(result.ImagesResults) == 0 {
		return "", fmt.Errorf("no Google Images results for scene %d", sceneIndex)
	}

	for _, img := range result.ImagesResults {
		outFile := filepath.Join(outputDir, fmt.Sprintf("proof_%03d_google.jpg", sceneIndex))
		if err := ps.downloadFile(ctx, img.Original, outFile); err == nil {
			log.Printf("[proof] Scene %d: Google image found from %s", sceneIndex, img.Source)
			return outFile, nil
		}
	}

	return "", fmt.Errorf("all Google Images failed to download")
}

func (ps *ProofScraper) downloadFile(ctx context.Context, fileURL, outPath string) error {
	req, err := http.NewRequestWithContext(ctx, "GET", fileURL, nil)
	if err != nil {
		return err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (compatible; TrueCrimePipeline/1.0)")
	req.Header.Set("Referer", "https://www.google.com")

	resp, err := ps.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	data, err := io.ReadAll(io.LimitReader(resp.Body, 10*1024*1024)) // max 10MB
	if err != nil {
		return err
	}

	if len(data) < 1000 {
		return fmt.Errorf("file too small (%d bytes)", len(data))
	}

	return os.WriteFile(outPath, data, 0644)
}

// extractSearchQuery pulls key named entities from narration text
func extractSearchQuery(text string) string {
	// Remove common filler words and keep meaningful terms
	filler := []string{
		"the", "a", "an", "was", "were", "had", "have", "has",
		"her", "his", "their", "they", "she", "he", "it", "this",
		"that", "and", "or", "but", "for", "from", "with", "into",
		"nobody", "somebody", "everyone", "anyone", "three", "two",
	}

	words := strings.Fields(text)
	var kept []string
	fillerSet := make(map[string]bool)
	for _, f := range filler {
		fillerSet[f] = true
	}

	for _, w := range words {
		clean := strings.ToLower(strings.Trim(w, ".,!?\"'"))
		if !fillerSet[clean] && len(clean) > 3 {
			kept = append(kept, clean)
		}
	}

	// Take first 4 meaningful words
	if len(kept) > 4 {
		kept = kept[:4]
	}

	return strings.Join(kept, " ")
}
