package sfx

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"true-crime-pipeline/config"
	"true-crime-pipeline/types"
)

// Matcher matches and prepares SFX for each scene
type Matcher struct {
	cfg     *config.Config
	sfxTags map[string][]string // sfx filename → mood tags
}

// New creates a new SFX Matcher
func New(cfg *config.Config) *Matcher {
	tags := loadSFXTags(cfg.Paths.SFXTags)
	return &Matcher{cfg: cfg, sfxTags: tags}
}

// Run assigns SFX files to each scene based on mood
func (m *Matcher) Run(ctx context.Context, script *types.Script, outputDir string) error {
	if !m.cfg.SFX.Enabled {
		log.Println("[sfx] SFX disabled in config — skipping")
		return nil
	}

	log.Println("[sfx] Matching SFX to scenes...")

	sfxDir := filepath.Join(outputDir, "sfx")
	if err := os.MkdirAll(sfxDir, 0755); err != nil {
		return err
	}

	for i := range script.Scenes {
		scene := &script.Scenes[i]

		sfxFile := m.pickSFX(scene.Mood)
		if sfxFile == "" {
			log.Printf("[sfx] Scene %d: no SFX for mood %q", i, scene.Mood)
			continue
		}

		fullPath := filepath.Join(m.cfg.Paths.AssetsSFX, sfxFile)
		if _, err := os.Stat(fullPath); err != nil {
			log.Printf("[sfx] Scene %d: SFX file not found: %s", i, fullPath)
			continue
		}

		// Prepare SFX: trim/loop to match scene duration + apply volume
		prepared, err := m.prepareSFX(ctx, fullPath, scene, sfxDir)
		if err != nil {
			log.Printf("[sfx] Scene %d: SFX prep failed: %v", i, err)
			continue
		}

		scene.SFXFile = prepared
		log.Printf("[sfx] Scene %d: %s → %s (mood: %s)", i, sfxFile, filepath.Base(prepared), scene.Mood)
	}

	log.Println("[sfx] ✅ SFX matching complete")
	return nil
}

// pickSFX returns the SFX filename for a mood, using config map first then tag matching
func (m *Matcher) pickSFX(mood string) string {
	// Try direct config map first
	if sfxFile, ok := m.cfg.SFX.MoodToSFXMap[mood]; ok {
		return sfxFile
	}

	// Tag-based fallback: find SFX whose tags include the mood
	for file, tags := range m.sfxTags {
		for _, tag := range tags {
			if strings.ToLower(tag) == strings.ToLower(mood) {
				return file
			}
		}
	}

	// Default fallback: use "eerie" or first available
	if sfxFile, ok := m.cfg.SFX.MoodToSFXMap["eerie"]; ok {
		return sfxFile
	}

	for file := range m.sfxTags {
		return file // return any available SFX
	}

	return ""
}

// prepareSFX trims/loops an SFX file to match scene duration and applies volume
func (m *Matcher) prepareSFX(ctx context.Context, sfxPath string, scene *types.ScriptScene, outputDir string) (string, error) {
	outFile := filepath.Join(outputDir, fmt.Sprintf("sfx_%03d.mp3", scene.Index))
	duration := scene.AudioDurationSec
	if duration <= 0 {
		duration = 5.0
	}

	// Get SFX duration
	sfxDur, err := getAudioDuration(sfxPath)
	if err != nil {
		sfxDur = duration
	}

	volume := m.cfg.SFX.VolumeUnderNarration
	fadeIn := m.cfg.SFX.FadeInSec
	fadeOut := m.cfg.SFX.FadeOutSec

	// Build audio filter: volume + fade in/out
	audioFilter := fmt.Sprintf(
		"volume=%.2f,afade=t=in:st=0:d=%.2f,afade=t=out:st=%.3f:d=%.2f",
		volume,
		fadeIn,
		duration-fadeOut,
		fadeOut,
	)

	var cmd *exec.Cmd
	if sfxDur >= duration {
		// Trim SFX to scene duration
		cmd = exec.CommandContext(ctx, "ffmpeg", "-y",
			"-i", sfxPath,
			"-t", fmt.Sprintf("%.3f", duration),
			"-af", audioFilter,
			outFile,
		)
	} else {
		// Loop SFX to fill scene duration
		loops := int(duration/sfxDur) + 2
		cmd = exec.CommandContext(ctx, "ffmpeg", "-y",
			"-stream_loop", fmt.Sprintf("%d", loops),
			"-i", sfxPath,
			"-t", fmt.Sprintf("%.3f", duration),
			"-af", audioFilter,
			outFile,
		)
	}

	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("ffmpeg SFX prep: %w", err)
	}
	return outFile, nil
}

func loadSFXTags(path string) map[string][]string {
	tags := make(map[string][]string)
	data, err := os.ReadFile(path)
	if err != nil {
		return tags
	}
	_ = json.Unmarshal(data, &tags)
	return tags
}

func getAudioDuration(path string) (float64, error) {
	out, err := exec.Command("ffprobe",
		"-v", "error",
		"-show_entries", "format=duration",
		"-of", "default=noprint_wrappers=1:nokey=1",
		path,
	).Output()
	if err != nil {
		return 0, err
	}
	var dur float64
	_, err = fmt.Sscanf(strings.TrimSpace(string(out)), "%f", &dur)
	return dur, err
}
