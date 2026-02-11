package visuals

import (
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"os"
	"path/filepath"
	"strings"

	"true-crime-pipeline/config"
	"true-crime-pipeline/types"
)

// AssetManager picks video clips from /assets/video/ for cinematic scenes
type AssetManager struct {
	cfg       *config.Config
	tags      map[string][]string // filename → tags
	usageLog  map[string][]string // runID → []filenames used
	runID     string
	usedInRun map[string]bool
}

// NewAssetManager loads tags and usage log
func NewAssetManager(cfg *config.Config, runID string) (*AssetManager, error) {
	tags, err := loadTagsJSON(cfg.Paths.VideoTags)
	if err != nil {
		return nil, fmt.Errorf("load video tags: %w", err)
	}

	usageLog := loadUsageLog(cfg.Paths.ClipUsageLog)

	return &AssetManager{
		cfg:       cfg,
		tags:      tags,
		usageLog:  usageLog,
		runID:     runID,
		usedInRun: make(map[string]bool),
	}, nil
}

// Pick selects the best matching clip for a scene's asset tags
// It never repeats the same clip within a single video run
func (am *AssetManager) Pick(scene *types.ScriptScene) (string, error) {
	if len(am.tags) == 0 {
		return "", fmt.Errorf("no video assets found in %s", am.cfg.Paths.AssetsVideo)
	}

	// Score every clip against the scene's asset tags
	type scored struct {
		file  string
		score int
	}
	var candidates []scored

	for file, clipTags := range am.tags {
		// Skip if already used in this video
		if am.usedInRun[file] {
			continue
		}

		score := matchScore(scene.AssetTags, clipTags, scene.Mood)
		if score >= 0 {
			candidates = append(candidates, scored{file, score})
		}
	}

	if len(candidates) == 0 {
		// All clips used — fallback to random from unused
		for file := range am.tags {
			if !am.usedInRun[file] {
				candidates = append(candidates, scored{file, 0})
			}
		}
	}

	if len(candidates) == 0 {
		return "", fmt.Errorf("all %d video clips have been used in this video", len(am.tags))
	}

	// Sort by score descending, then pick from top 3 randomly (prevents always same clip)
	sortScored(candidates)
	topN := 3
	if len(candidates) < topN {
		topN = len(candidates)
	}
	pick := candidates[rand.Intn(topN)]

	// Mark as used
	am.usedInRun[pick.file] = true
	am.usageLog[am.runID] = append(am.usageLog[am.runID], pick.file)
	am.saveUsageLog()

	fullPath := filepath.Join(am.cfg.Paths.AssetsVideo, pick.file)
	log.Printf("[assets] Scene %d: picked clip %q (score: %d)", scene.Index, pick.file, pick.score)
	return fullPath, nil
}

// matchScore scores a clip against required tags + mood
func matchScore(required []string, clipTags []string, mood string) int {
	clipTagSet := make(map[string]bool)
	for _, t := range clipTags {
		clipTagSet[strings.ToLower(t)] = true
	}

	score := 0
	for _, req := range required {
		if clipTagSet[strings.ToLower(req)] {
			score += 10
		}
	}

	// Mood bonus
	if clipTagSet[strings.ToLower(mood)] {
		score += 15
	}

	return score
}

func sortScored(s []struct {
	file  string
	score int
}) {
	for i := 1; i < len(s); i++ {
		for j := i; j > 0 && s[j].score > s[j-1].score; j-- {
			s[j], s[j-1] = s[j-1], s[j]
		}
	}
}

func loadTagsJSON(path string) (map[string][]string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			// Return empty map — user hasn't added clips yet
			log.Printf("[assets] Warning: tags.json not found at %s — no asset clips will be used", path)
			return make(map[string][]string), nil
		}
		return nil, err
	}

	// tags.json may have _instructions and _tag_options keys — skip those
	var raw map[string]json.RawMessage
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, err
	}

	result := make(map[string][]string)
	for k, v := range raw {
		if strings.HasPrefix(k, "_") {
			continue
		}
		var tags []string
		if err := json.Unmarshal(v, &tags); err != nil {
			continue
		}
		result[k] = tags
	}
	return result, nil
}

func loadUsageLog(path string) map[string][]string {
	log := make(map[string][]string)
	data, err := os.ReadFile(path)
	if err != nil {
		return log
	}
	_ = json.Unmarshal(data, &log)
	return log
}

func (am *AssetManager) saveUsageLog() {
	data, _ := json.MarshalIndent(am.usageLog, "", "  ")
	_ = os.WriteFile(am.cfg.Paths.ClipUsageLog, data, 0644)
}
