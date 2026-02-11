package visuals

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

// Assembler coordinates all visual preparation for the pipeline
type Assembler struct {
	cfg           *config.Config
	assetManager  *AssetManager
	pollinations  *PollinationsFetcher
	proofScraper  *ProofScraper
}

// NewAssembler creates a new visual Assembler
func NewAssembler(cfg *config.Config, runID string) (*Assembler, error) {
	am, err := NewAssetManager(cfg, runID)
	if err != nil {
		return nil, err
	}

	return &Assembler{
		cfg:          cfg,
		assetManager: am,
		pollinations: NewPollinationsFetcher(),
		proofScraper: NewProofScraper(),
	}, nil
}

// Run prepares all visual files for every scene
func (a *Assembler) Run(ctx context.Context, script *types.Script, story *types.Story, outputDir string) error {
	log.Println("[visuals] Preparing visual assets for all scenes...")

	visualDir := filepath.Join(outputDir, "visuals")
	if err := os.MkdirAll(visualDir, 0755); err != nil {
		return err
	}

	for i := range script.Scenes {
		scene := &script.Scenes[i]
		log.Printf("[visuals] Scene %d/%d (%s, mood: %s)", i+1, len(script.Scenes), scene.SceneType, scene.Mood)

		switch scene.SceneType {
		case "cinematic":
			clip, err := a.assetManager.Pick(scene)
			if err != nil {
				log.Printf("[visuals] Warning scene %d: %v — using dramatic fallback", i, err)
				// Fall through to dramatic
				scene.SceneType = "dramatic"
				if scene.ImagePrompt == "" {
					scene.ImagePrompt = fmt.Sprintf("dark crime scene %s atmosphere cinematic", scene.Mood)
				}
				img, err := a.pollinations.Fetch(ctx, scene, visualDir)
				if err != nil {
					return fmt.Errorf("scene %d visual fallback failed: %w", i, err)
				}
				prepared, err := a.prepareImageWithKenBurns(ctx, img, scene, visualDir)
				if err != nil {
					return err
				}
				scene.VisualFile = prepared
			} else {
				prepared, err := a.prepareVideoClip(ctx, clip, scene, visualDir)
				if err != nil {
					return fmt.Errorf("scene %d clip prep failed: %w", i, err)
				}
				scene.VisualFile = prepared
			}

		case "dramatic":
			img, err := a.pollinations.Fetch(ctx, scene, visualDir)
			if err != nil {
				log.Printf("[visuals] Warning scene %d: Pollinations failed: %v — using dark fallback", i, err)
				// Use a black frame as absolute fallback
				img = a.createFallbackFrame(visualDir, i)
			}
			prepared, err := a.prepareImageWithKenBurns(ctx, img, scene, visualDir)
			if err != nil {
				return err
			}
			scene.VisualFile = prepared

		case "proof":
			img, err := a.proofScraper.FetchProofImage(ctx, scene, story, visualDir)
			if err != nil {
				log.Printf("[visuals] Warning scene %d: no proof image found: %v", i, err)
				// Fall back to dramatic for this scene
				scene.SceneType = "dramatic"
				if scene.ImagePrompt == "" {
					scene.ImagePrompt = "evidence document crime scene investigation cinematic"
				}
				img2, err2 := a.pollinations.Fetch(ctx, scene, visualDir)
				if err2 != nil {
					img2 = a.createFallbackFrame(visualDir, i)
				}
				prepared, err3 := a.prepareImageWithKenBurns(ctx, img2, scene, visualDir)
				if err3 != nil {
					return err3
				}
				scene.VisualFile = prepared
			} else {
				// Proof scene: add source credit overlay
				credited, err := a.addSourceCredit(ctx, img, scene, story, visualDir)
				if err != nil {
					credited = img // use without credit if it fails
				}
				scene.VisualFile = credited
			}
		}

		log.Printf("[visuals] ✅ Scene %d visual ready: %s", i, scene.VisualFile)
	}

	return nil
}

// prepareVideoClip trims or loops a video clip to match the scene's narration duration
func (a *Assembler) prepareVideoClip(ctx context.Context, clipPath string, scene *types.ScriptScene, outputDir string) (string, error) {
	outFile := filepath.Join(outputDir, fmt.Sprintf("clip_%03d.mp4", scene.Index))
	duration := scene.AudioDurationSec
	if duration <= 0 {
		duration = 5.0
	}

	// Get clip duration
	clipDur, err := getVideoDuration(clipPath)
	if err != nil {
		clipDur = duration // assume same length if we can't measure
	}

	var cmd *exec.Cmd
	if clipDur >= duration {
		// Trim to exact duration
		cmd = exec.CommandContext(ctx, "ffmpeg", "-y",
			"-i", clipPath,
			"-t", fmt.Sprintf("%.3f", duration),
			"-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
			"-c:v", "libx264",
			"-preset", "fast",
			"-crf", "23",
			"-an", // no audio from clip
			outFile,
		)
	} else {
		// Loop the clip to fill the duration
		loops := int(duration/clipDur) + 2
		cmd = exec.CommandContext(ctx, "ffmpeg", "-y",
			"-stream_loop", fmt.Sprintf("%d", loops),
			"-i", clipPath,
			"-t", fmt.Sprintf("%.3f", duration),
			"-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
			"-c:v", "libx264",
			"-preset", "fast",
			"-crf", "23",
			"-an",
			outFile,
		)
	}

	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("ffmpeg clip prep: %w", err)
	}
	return outFile, nil
}

// prepareImageWithKenBurns applies slow Ken Burns zoom to a still image
func (a *Assembler) prepareImageWithKenBurns(ctx context.Context, imgPath string, scene *types.ScriptScene, outputDir string) (string, error) {
	outFile := filepath.Join(outputDir, fmt.Sprintf("kenburns_%03d.mp4", scene.Index))
	duration := scene.AudioDurationSec
	if duration <= 0 {
		duration = 5.0
	}

	zoom := a.cfg.Visuals.KenBurnsZoomFactor
	fps := a.cfg.Visuals.FPS
	totalFrames := int(duration * float64(fps))

	// Ken Burns: slow zoom in from 1.0 to zoom factor
	// zoompan filter: z='min(zoom+0.0005,1.08)', x='iw/2-(iw/zoom/2)', y='ih/2-(ih/zoom/2)'
	zoomStep := (zoom - 1.0) / float64(totalFrames)
	zoomFilter := fmt.Sprintf(
		"scale=3840:2160,zoompan=z='min(zoom+%.6f,%.3f)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=%d:fps=%d,scale=1920:1080",
		zoomStep, zoom, totalFrames, fps,
	)

	cmd := exec.CommandContext(ctx, "ffmpeg", "-y",
		"-loop", "1",
		"-i", imgPath,
		"-vf", zoomFilter,
		"-t", fmt.Sprintf("%.3f", duration),
		"-c:v", "libx264",
		"-preset", "fast",
		"-crf", "23",
		"-pix_fmt", "yuv420p",
		"-an",
		outFile,
	)

	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("ffmpeg ken burns: %w", err)
	}
	return outFile, nil
}

// addSourceCredit burns a source credit overlay onto the proof image
func (a *Assembler) addSourceCredit(ctx context.Context, imgPath string, scene *types.ScriptScene, story *types.Story, outputDir string) (string, error) {
	outFile := filepath.Join(outputDir, fmt.Sprintf("proof_credited_%03d.jpg", scene.Index))

	credit := fmt.Sprintf("Source: %s", story.Source)
	if story.PublishedAt != "" && len(story.PublishedAt) >= 4 {
		credit += ", " + story.PublishedAt[:4]
	}

	// FFmpeg drawtext filter for source credit
	drawtextFilter := fmt.Sprintf(
		"scale=960:640,drawtext=text='%s':fontcolor=white:fontsize=18:box=1:boxcolor=black@0.6:boxborderw=5:x=w-tw-10:y=h-th-10",
		escapeFFmpegText(credit),
	)

	cmd := exec.CommandContext(ctx, "ffmpeg", "-y",
		"-i", imgPath,
		"-vf", drawtextFilter,
		"-q:v", "2",
		outFile,
	)
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("ffmpeg source credit: %w", err)
	}
	return outFile, nil
}

// createFallbackFrame creates a solid dark frame when no visual is available
func (a *Assembler) createFallbackFrame(outputDir string, sceneIndex int) string {
	outFile := filepath.Join(outputDir, fmt.Sprintf("fallback_%03d.jpg", sceneIndex))
	_ = exec.Command("ffmpeg", "-y",
		"-f", "lavfi",
		"-i", "color=c=black:s=1920x1080:d=1",
		"-frames:v", "1",
		outFile,
	).Run()
	return outFile
}

func getVideoDuration(path string) (float64, error) {
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

func escapeFFmpegText(s string) string {
	s = strings.ReplaceAll(s, "'", "\\'")
	s = strings.ReplaceAll(s, ":", "\\:")
	return s
}
