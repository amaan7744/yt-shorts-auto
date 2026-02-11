package audio

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"true-crime-pipeline/config"
	"true-crime-pipeline/types"
)

// Generator handles TTS audio generation
type Generator struct {
	cfg *config.Config
}

// New creates a new Generator
func New(cfg *config.Config) *Generator {
	return &Generator{cfg: cfg}
}

// Run generates audio for every scene in the script.
// It calls your existing TTS binary/script via shell.
// Set TTS_COMMAND in your .env to the command that accepts:
//   --text "..." --output path/to/file.mp3
// If TTS_COMMAND is not set, it falls back to edge-tts (free Microsoft TTS).
func (g *Generator) Run(ctx context.Context, script *types.Script, outputDir string) error {
	log.Println("[audio] Generating TTS audio for all scenes...")

	if err := os.MkdirAll(outputDir, 0755); err != nil {
		return fmt.Errorf("create audio dir: %w", err)
	}

	ttsCmd := os.Getenv("TTS_COMMAND")
	if ttsCmd == "" {
		// Check if edge-tts is available as fallback
		if _, err := exec.LookPath("edge-tts"); err == nil {
			ttsCmd = "edge-tts"
			log.Println("[audio] Using edge-tts as TTS engine (fallback)")
		} else {
			return fmt.Errorf("no TTS engine found. Set TTS_COMMAND in .env or install edge-tts: pip install edge-tts")
		}
	}

	for i := range script.Scenes {
		scene := &script.Scenes[i]
		outFile := filepath.Join(outputDir, fmt.Sprintf("scene_%03d.mp3", i))

		log.Printf("[audio] Scene %d/%d: generating audio...", i+1, len(script.Scenes))

		if err := g.generateSceneAudio(ctx, ttsCmd, scene.Narration, outFile); err != nil {
			return fmt.Errorf("scene %d TTS failed: %w", i, err)
		}

		// Measure actual duration
		dur, err := getAudioDuration(outFile)
		if err != nil {
			log.Printf("[audio] Warning: could not measure duration for scene %d, using estimate", i)
		} else {
			scene.AudioDurationSec = dur
		}

		scene.AudioFile = outFile
		log.Printf("[audio] Scene %d: %.2fs → %s", i, scene.AudioDurationSec, outFile)
	}

	// Recalculate timestamps from real audio durations
	recalcTimestamps(script)

	// Concatenate all segments into one final audio file
	finalAudio := filepath.Join(outputDir, "audio_final.mp3")
	if err := g.concatenateAudio(script, outputDir, finalAudio); err != nil {
		return fmt.Errorf("concatenate audio: %w", err)
	}

	log.Printf("[audio] ✅ Final audio: %s (total: %.1fs)", finalAudio, script.TotalSec)
	return nil
}

func (g *Generator) generateSceneAudio(ctx context.Context, ttsCmd, text, outFile string) error {
	ttsCmd = strings.TrimSpace(ttsCmd)

	var cmd *exec.Cmd

	switch {
	case ttsCmd == "edge-tts":
		// edge-tts --text "..." --write-media out.mp3
		cmd = exec.CommandContext(ctx,
			"edge-tts",
			"--voice", "en-US-GuyNeural",
			"--text", text,
			"--write-media", outFile,
		)

	case strings.HasSuffix(ttsCmd, ".py"):
		// Custom Python TTS script
		cmd = exec.CommandContext(ctx,
			"python3", ttsCmd,
			"--text", text,
			"--output", outFile,
		)

	default:
		// Generic: pass text and output as args
		cmd = exec.CommandContext(ctx,
			ttsCmd,
			"--text", text,
			"--output", outFile,
		)
	}

	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	// Retry up to 3 times
	var err error
	for attempt := 1; attempt <= 3; attempt++ {
		err = cmd.Run()
		if err == nil {
			return nil
		}
		log.Printf("[audio] TTS attempt %d failed: %v — retrying...", attempt, err)
		time.Sleep(time.Duration(attempt) * 2 * time.Second)
	}
	return err
}

// concatenateAudio uses ffmpeg to join all scene audio files in order
func (g *Generator) concatenateAudio(script *types.Script, audioDir, outputFile string) error {
	// Build ffmpeg concat list
	listFile := filepath.Join(audioDir, "concat_list.txt")
	var lines []string
	for _, scene := range script.Scenes {
		if scene.AudioFile != "" {
			lines = append(lines, fmt.Sprintf("file '%s'", scene.AudioFile))
		}
	}

	if err := os.WriteFile(listFile, []byte(strings.Join(lines, "\n")), 0644); err != nil {
		return err
	}

	cmd := exec.Command("ffmpeg", "-y",
		"-f", "concat",
		"-safe", "0",
		"-i", listFile,
		"-c", "copy",
		outputFile,
	)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

// getAudioDuration uses ffprobe to get accurate audio duration in seconds
func getAudioDuration(audioFile string) (float64, error) {
	out, err := exec.Command("ffprobe",
		"-v", "error",
		"-show_entries", "format=duration",
		"-of", "default=noprint_wrappers=1:nokey=1",
		audioFile,
	).Output()
	if err != nil {
		return 0, err
	}
	var dur float64
	_, err = fmt.Sscanf(strings.TrimSpace(string(out)), "%f", &dur)
	return dur, err
}

// recalcTimestamps updates scene timestamps based on real measured audio durations
func recalcTimestamps(script *types.Script) {
	var elapsed float64
	for i := range script.Scenes {
		script.Scenes[i].TimestampStart = elapsed
		elapsed += script.Scenes[i].AudioDurationSec
		script.Scenes[i].TimestampEnd = elapsed
	}
	script.TotalSec = elapsed
}
