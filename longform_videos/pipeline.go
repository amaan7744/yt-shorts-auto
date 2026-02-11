package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"time"

	"true-crime-pipeline/01_research"
	"true-crime-pipeline/02_script"
	"true-crime-pipeline/03_audio"
	"true-crime-pipeline/04_visuals"
	"true-crime-pipeline/05_subtitles"
	"true-crime-pipeline/06_sfx"
	"true-crime-pipeline/07_render"
	"true-crime-pipeline/08_metadata"
	"true-crime-pipeline/09_upload"
	"true-crime-pipeline/config"
	"true-crime-pipeline/types"

	"github.com/google/uuid"
	"github.com/joho/godotenv"
)

func main() {
	// Load .env (local dev only — GitHub Actions uses Secrets)
	_ = godotenv.Load()

	// Load config
	cfg, err := config.Load("config.yaml")
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// Ensure required dirs exist
	for _, dir := range []string{cfg.Paths.Output, cfg.Paths.Logs, cfg.Paths.AssetsVideo, cfg.Paths.AssetsSFX} {
		if err := os.MkdirAll(dir, 0755); err != nil {
			log.Fatalf("Failed to create dir %s: %v", dir, err)
		}
	}

	// Create run ID and output dir for this run
	runID := uuid.NewString()[:8]
	runDir := filepath.Join(cfg.Paths.Output, runID)
	if err := os.MkdirAll(runDir, 0755); err != nil {
		log.Fatalf("Failed to create run dir: %v", err)
	}

	log.Printf("🎬 TrueCrime Pipeline starting — Run ID: %s", runID)
	log.Printf("📁 Output dir: %s", runDir)

	ctx := context.Background()
	state := &types.PipelineState{
		RunID:     runID,
		StartedAt: time.Now().UTC().Format(time.RFC3339),
	}

	// Save state on exit
	defer func() {
		state.CompletedAt = time.Now().UTC().Format(time.RFC3339)
		saveState(state, runDir)
		if state.Error != "" {
			log.Printf("❌ Pipeline failed: %s", state.Error)
			os.Exit(1)
		}
		log.Printf("✅ Pipeline complete! Video: %s", state.YouTubeURL)
	}()

	// ─────────────────────────────────────────────
	// STAGE 1: Research
	// ─────────────────────────────────────────────
	log.Println("\n━━━ STAGE 1: Research ━━━")
	scraper := research.New(cfg)
	story, err := scraper.Run(ctx)
	if err != nil {
		state.Error = fmt.Sprintf("Stage 1 Research: %v", err)
		return
	}
	state.Story = story
	saveJSON(filepath.Join(runDir, "story.json"), story)

	// ─────────────────────────────────────────────
	// STAGE 2: Script Writing
	// ─────────────────────────────────────────────
	log.Println("\n━━━ STAGE 2: Script Writing ━━━")
	writer := script.New(cfg)
	scriptData, err := writer.Run(ctx, story)
	if err != nil {
		state.Error = fmt.Sprintf("Stage 2 Script: %v", err)
		return
	}
	state.Script = scriptData
	saveJSON(filepath.Join(runDir, "script.json"), scriptData)

	// ─────────────────────────────────────────────
	// STAGE 3: Audio Generation
	// ─────────────────────────────────────────────
	log.Println("\n━━━ STAGE 3: Audio Generation ━━━")
	audioDir := filepath.Join(runDir, "audio")
	audioGen := audio.New(cfg)
	if err := audioGen.Run(ctx, scriptData, audioDir); err != nil {
		state.Error = fmt.Sprintf("Stage 3 Audio: %v", err)
		return
	}
	finalAudio := filepath.Join(audioDir, "audio_final.mp3")
	state.AudioFile = finalAudio
	// Re-save script with updated audio timestamps
	saveJSON(filepath.Join(runDir, "script.json"), scriptData)

	// ─────────────────────────────────────────────
	// STAGE 4: Visuals
	// ─────────────────────────────────────────────
	log.Println("\n━━━ STAGE 4: Visuals ━━━")
	visualDir := filepath.Join(runDir, "visuals")
	assembler, err := visuals.NewAssembler(cfg, runID)
	if err != nil {
		state.Error = fmt.Sprintf("Stage 4 Visuals init: %v", err)
		return
	}
	if err := assembler.Run(ctx, scriptData, story, visualDir); err != nil {
		state.Error = fmt.Sprintf("Stage 4 Visuals: %v", err)
		return
	}
	// Re-save script with visual file paths
	saveJSON(filepath.Join(runDir, "script.json"), scriptData)

	// ─────────────────────────────────────────────
	// STAGE 5: Subtitles
	// ─────────────────────────────────────────────
	log.Println("\n━━━ STAGE 5: Subtitles ━━━")
	subtitleDir := filepath.Join(runDir, "subtitles")
	subGen := subtitles.New(cfg)
	srtFile, err := subGen.Run(ctx, finalAudio, subtitleDir)
	if err != nil {
		log.Printf("⚠️  Stage 5 Subtitles failed: %v — continuing without subtitles", err)
		srtFile = ""
	}

	// ─────────────────────────────────────────────
	// STAGE 6: SFX
	// ─────────────────────────────────────────────
	log.Println("\n━━━ STAGE 6: SFX Matching ━━━")
	sfxMatcher := sfx.New(cfg)
	if err := sfxMatcher.Run(ctx, scriptData, runDir); err != nil {
		log.Printf("⚠️  Stage 6 SFX failed: %v — continuing without SFX", err)
	}

	// ─────────────────────────────────────────────
	// STAGE 7: Render
	// ─────────────────────────────────────────────
	log.Println("\n━━━ STAGE 7: Rendering ━━━")
	renderer := render.New(cfg)
	finalVideo, err := renderer.Run(ctx, scriptData, finalAudio, runDir)
	if err != nil {
		state.Error = fmt.Sprintf("Stage 7 Render: %v", err)
		return
	}
	state.VideoFile = finalVideo

	// Burn subtitles into video if available
	if srtFile != "" {
		subtitledVideo, err := subGen.BurnIntoVideo(ctx, finalVideo, srtFile, runDir)
		if err != nil {
			log.Printf("⚠️  Subtitle burn failed: %v — using video without subtitles", err)
		} else {
			state.VideoFile = subtitledVideo
			finalVideo = subtitledVideo
		}
	}

	// ─────────────────────────────────────────────
	// STAGE 8: Metadata
	// ─────────────────────────────────────────────
	log.Println("\n━━━ STAGE 8: Metadata Generation ━━━")
	metaGen := metadata.New(cfg)
	videoMetadata, err := metaGen.Run(ctx, scriptData, story)
	if err != nil {
		state.Error = fmt.Sprintf("Stage 8 Metadata: %v", err)
		return
	}
	state.Metadata = videoMetadata
	saveJSON(filepath.Join(runDir, "metadata.json"), videoMetadata)

	// ─────────────────────────────────────────────
	// STAGE 9: Upload
	// ─────────────────────────────────────────────
	log.Println("\n━━━ STAGE 9: YouTube Upload ━━━")
	uploader := upload.New(cfg)
	videoID, videoURL, err := uploader.Run(ctx, finalVideo, videoMetadata)
	if err != nil {
		state.Error = fmt.Sprintf("Stage 9 Upload: %v", err)
		return
	}
	state.YouTubeID = videoID
	state.YouTubeURL = videoURL

	// Log upload
	_ = upload.LogUpload(videoID, videoURL, finalVideo, cfg.Paths.Logs, videoMetadata)
}

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

func saveState(state *types.PipelineState, dir string) {
	saveJSON(filepath.Join(dir, "pipeline_state.json"), state)
}

func saveJSON(path string, v interface{}) {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		log.Printf("Warning: could not marshal JSON for %s: %v", path, err)
		return
	}
	if err := os.WriteFile(path, data, 0644); err != nil {
		log.Printf("Warning: could not save %s: %v", path, err)
	}
}
