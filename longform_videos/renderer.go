package render

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"true-crime-pipeline/config"
	"true-crime-pipeline/types"
)

// Renderer assembles the final video from all prepared assets
type Renderer struct {
	cfg *config.Config
}

// New creates a new Renderer
func New(cfg *config.Config) *Renderer {
	return &Renderer{cfg: cfg}
}

// Run builds the final video: visuals + audio + proof animations + SFX
func (r *Renderer) Run(ctx context.Context, script *types.Script, audioFile, outputDir string) (string, error) {
	log.Println("[render] Starting final video assembly...")

	// Step 1: Concatenate all scene visuals into one video (no audio)
	silentVideo, err := r.concatenateVisuals(ctx, script, outputDir)
	if err != nil {
		return "", fmt.Errorf("concatenate visuals: %w", err)
	}

	// Step 2: Overlay proof images as slide-in animations
	proofVideo, err := r.applyProofOverlays(ctx, script, silentVideo, outputDir)
	if err != nil {
		log.Printf("[render] Warning: proof overlays failed: %v — continuing without them", err)
		proofVideo = silentVideo
	}

	// Step 3: Mix narration audio + SFX
	mixedAudio, err := r.mixAudio(ctx, script, audioFile, outputDir)
	if err != nil {
		log.Printf("[render] Warning: SFX mix failed: %v — using narration only", err)
		mixedAudio = audioFile
	}

	// Step 4: Combine video + audio into final MP4
	finalVideo, err := r.combineVideoAudio(ctx, proofVideo, mixedAudio, outputDir)
	if err != nil {
		return "", fmt.Errorf("combine video+audio: %w", err)
	}

	log.Printf("[render] ✅ Final video ready: %s", finalVideo)
	return finalVideo, nil
}

// concatenateVisuals joins all scene visual files in order
func (r *Renderer) concatenateVisuals(ctx context.Context, script *types.Script, outputDir string) (string, error) {
	log.Println("[render] Concatenating scene visuals...")

	listFile := filepath.Join(outputDir, "visuals_concat.txt")
	var lines []string
	for _, scene := range script.Scenes {
		if scene.VisualFile != "" {
			lines = append(lines, fmt.Sprintf("file '%s'", scene.VisualFile))
		}
	}

	if len(lines) == 0 {
		return "", fmt.Errorf("no visual files found in script scenes")
	}

	if err := os.WriteFile(listFile, []byte(strings.Join(lines, "\n")), 0644); err != nil {
		return "", err
	}

	outFile := filepath.Join(outputDir, "visuals_raw.mp4")
	cmd := exec.CommandContext(ctx, "ffmpeg", "-y",
		"-f", "concat",
		"-safe", "0",
		"-i", listFile,
		"-c:v", "libx264",
		"-preset", "fast",
		"-crf", "22",
		"-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1",
		"-r", fmt.Sprintf("%d", r.cfg.Visuals.FPS),
		"-pix_fmt", "yuv420p",
		"-an",
		outFile,
	)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("ffmpeg concat visuals: %w", err)
	}
	return outFile, nil
}

// applyProofOverlays adds slide-in proof image animations over the main video
func (r *Renderer) applyProofOverlays(ctx context.Context, script *types.Script, videoFile, outputDir string) (string, error) {
	// Collect all proof scenes
	var proofScenes []types.ScriptScene
	for _, scene := range script.Scenes {
		if scene.SceneType == "proof" && scene.VisualFile != "" {
			proofScenes = append(proofScenes, scene)
		}
	}

	if len(proofScenes) == 0 {
		log.Println("[render] No proof scenes — skipping overlay step")
		return videoFile, nil
	}

	log.Printf("[render] Applying %d proof overlay(s)...", len(proofScenes))

	currentVideo := videoFile
	for i, scene := range proofScenes {
		overlaid, err := r.applyOneProofOverlay(ctx, currentVideo, scene, outputDir, i)
		if err != nil {
			log.Printf("[render] Warning: proof overlay %d failed: %v", i, err)
			continue
		}
		currentVideo = overlaid
	}

	return currentVideo, nil
}

// applyOneProofOverlay adds a single proof image slide-in/slide-out animation
// The proof image slides in from the right, covers 3:2 center, then slides back out
func (r *Renderer) applyOneProofOverlay(ctx context.Context, videoFile string, scene types.ScriptScene, outputDir string, idx int) (string, error) {
	outFile := filepath.Join(outputDir, fmt.Sprintf("proof_overlay_%02d.mp4", idx))

	startTime := scene.TimestampStart
	holdDuration := scene.ProofDurationSec
	if holdDuration <= 0 {
		holdDuration = r.cfg.Visuals.ProofHoldSecDefault
	}
	animDur := r.cfg.Visuals.ProofAnimationDurationSec
	endTime := startTime + holdDuration + animDur*2

	// Proof image dimensions: 960x640 (3:2) centered on 1920x1080
	proofW := 960
	proofH := 640
	centerX := (1920 - proofW) / 2 // 480
	centerY := (1080 - proofH) / 2 // 220

	// Slide from right edge (x=1920) to center (x=480) then back to right (x=1920)
	// x position formula using FFmpeg overlay timing:
	// slide in:  from 1920 to 480 over animDur seconds
	// hold:      at 480 for holdDuration seconds
	// slide out: from 480 to 1920 over animDur seconds

	slideInExpr := fmt.Sprintf(
		"if(lt(t-%.3f,%.3f), 1920+(%.0f-1920)*((t-%.3f)/%.3f), %.0f)",
		startTime, animDur,
		float64(centerX),
		startTime, animDur,
		float64(centerX),
	)

	slideOutStart := startTime + animDur + holdDuration
	xExpr := fmt.Sprintf(
		"if(lt(t,%.3f), %s, if(lt(t,%.3f), %.0f+(1920-%.0f)*((t-%.3f)/%.3f), 1920))",
		startTime+animDur,
		slideInExpr,
		slideOutStart+animDur,
		float64(centerX), float64(centerX),
		slideOutStart, animDur,
	)

	// Dim background when proof is visible
	dim := r.cfg.Visuals.BackgroundDimDuringProof
	brightnessExpr := fmt.Sprintf(
		"if(between(t,%.3f,%.3f), %.2f, 1.0)",
		startTime, endTime, dim,
	)

	// Build complex filter:
	// 1. Scale and add shadow/border to proof image
	// 2. Dim main video when proof is shown
	// 3. Overlay proof onto main video at animated position
	proofFilter := fmt.Sprintf(
		"[1:v]scale=%d:%d,pad=%d:%d:5:5:black[proof_bordered];"+
			"[0:v]eq=brightness='%s'[bg_dimmed];"+
			"[bg_dimmed][proof_bordered]overlay=x='%s':y=%d:enable='between(t,%.3f,%.3f)'[out]",
		proofW-10, proofH-10, // slightly smaller to show border
		proofW, proofH,
		brightnessExpr,
		xExpr,
		centerY,
		startTime, endTime,
	)

	// Scale proof image first to exact dimensions
	scaledProof := filepath.Join(outputDir, fmt.Sprintf("proof_scaled_%02d.jpg", idx))
	scaleCmd := exec.CommandContext(ctx, "ffmpeg", "-y",
		"-i", scene.VisualFile,
		"-vf", fmt.Sprintf("scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2:black", proofW, proofH, proofW, proofH),
		scaledProof,
	)
	if err := scaleCmd.Run(); err != nil {
		return "", fmt.Errorf("scale proof image: %w", err)
	}

	cmd := exec.CommandContext(ctx, "ffmpeg", "-y",
		"-i", videoFile,
		"-i", scaledProof,
		"-filter_complex", proofFilter,
		"-map", "[out]",
		"-c:v", "libx264",
		"-preset", "fast",
		"-crf", "22",
		"-pix_fmt", "yuv420p",
		"-an",
		outFile,
	)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("ffmpeg proof overlay: %w", err)
	}
	return outFile, nil
}

// mixAudio merges narration audio with SFX tracks
func (r *Renderer) mixAudio(ctx context.Context, script *types.Script, narrationFile, outputDir string) (string, error) {
	// Collect all SFX files with their timing
	var sfxInputs []string
	var sfxFilters []string
	inputIdx := 1 // 0 is narration

	for _, scene := range script.Scenes {
		if scene.SFXFile == "" {
			continue
		}
		sfxInputs = append(sfxInputs, "-i", scene.SFXFile)

		// Delay SFX to scene start time
		delayMs := int(scene.TimestampStart * 1000)
		sfxFilters = append(sfxFilters,
			fmt.Sprintf("[%d:a]adelay=%d|%d[sfx%d]", inputIdx, delayMs, delayMs, inputIdx),
		)
		inputIdx++
	}

	outFile := filepath.Join(outputDir, "audio_mixed.mp3")

	if len(sfxInputs) == 0 {
		// No SFX — just copy narration
		cmd := exec.CommandContext(ctx, "ffmpeg", "-y", "-i", narrationFile, "-c:a", "copy", outFile)
		return outFile, cmd.Run()
	}

	// Build amix filter
	var mixInputs []string
	mixInputs = append(mixInputs, "[0:a]")
	for i := range sfxFilters {
		mixInputs = append(mixInputs, fmt.Sprintf("[sfx%d]", i+1))
	}

	filterComplex := strings.Join(sfxFilters, ";")
	filterComplex += ";" + strings.Join(mixInputs, "") +
		fmt.Sprintf("amix=inputs=%d:duration=first:normalize=0[aout]", len(mixInputs))

	args := []string{"-y", "-i", narrationFile}
	args = append(args, sfxInputs...)
	args = append(args,
		"-filter_complex", filterComplex,
		"-map", "[aout]",
		"-c:a", "libmp3lame",
		"-q:a", "2",
		outFile,
	)

	cmd := exec.CommandContext(ctx, "ffmpeg", args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("ffmpeg audio mix: %w", err)
	}
	return outFile, nil
}

// combineVideoAudio merges the final video and audio into one MP4
func (r *Renderer) combineVideoAudio(ctx context.Context, videoFile, audioFile, outputDir string) (string, error) {
	log.Println("[render] Combining video + audio...")

	outFile := filepath.Join(outputDir, "final_video.mp4")

	cmd := exec.CommandContext(ctx, "ffmpeg", "-y",
		"-i", videoFile,
		"-i", audioFile,
		"-c:v", "copy",
		"-c:a", "aac",
		"-b:a", "192k",
		"-shortest",
		"-movflags", "+faststart", // optimize for web streaming
		outFile,
	)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("ffmpeg combine: %w", err)
	}
	return outFile, nil
}
