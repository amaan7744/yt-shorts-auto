package subtitles

import (
	"bufio"
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"true-crime-pipeline/config"
)

// Generator handles subtitle generation and burning
type Generator struct {
	cfg *config.Config
}

// New creates a new subtitle Generator
func New(cfg *config.Config) *Generator {
	return &Generator{cfg: cfg}
}

// Run transcribes audio with Whisper and produces an SRT file
func (g *Generator) Run(ctx context.Context, audioFile, outputDir string) (string, error) {
	log.Println("[subtitles] Running Whisper transcription...")

	if err := os.MkdirAll(outputDir, 0755); err != nil {
		return "", err
	}

	srtFile := filepath.Join(outputDir, "subtitles.srt")

	// Run whisper CLI
	// whisper audio.mp3 --model base --output_format srt --output_dir /path/
	cmd := exec.CommandContext(ctx,
		"whisper",
		audioFile,
		"--model", g.cfg.Subtitles.WhisperModel,
		"--output_format", "srt",
		"--output_dir", outputDir,
		"--language", "en",
		"--word_timestamps", "True",
		"--max_line_width", fmt.Sprintf("%d", g.cfg.Subtitles.MaxCharsPerLine),
		"--max_line_count", "2",
	)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("whisper failed: %w", err)
	}

	// Whisper saves as <audioFilename>.srt — find it
	base := strings.TrimSuffix(filepath.Base(audioFile), filepath.Ext(audioFile))
	whisperOut := filepath.Join(outputDir, base+".srt")
	if _, err := os.Stat(whisperOut); err == nil && whisperOut != srtFile {
		if err := os.Rename(whisperOut, srtFile); err != nil {
			srtFile = whisperOut // use the whisper path directly
		}
	}

	log.Printf("[subtitles] ✅ SRT generated: %s", srtFile)
	return srtFile, nil
}

// BurnIntoVideo uses FFmpeg to burn subtitles directly into the video
func (g *Generator) BurnIntoVideo(ctx context.Context, videoFile, srtFile, outputDir string) (string, error) {
	log.Println("[subtitles] Burning subtitles into video...")

	outFile := filepath.Join(outputDir, "video_subtitled.mp4")

	// Build FFmpeg subtitle filter with styling
	subtitleFilter := fmt.Sprintf(
		"subtitles=%s:force_style='FontName=%s,FontSize=%d,Bold=%d,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=%.0f,Alignment=2,MarginV=%d'",
		escapeSubtitlePath(srtFile),
		g.cfg.Subtitles.Font,
		g.cfg.Subtitles.FontSize,
		boolToInt(g.cfg.Subtitles.FontWeight == "bold"),
		g.cfg.Subtitles.StrokeWidth,
		g.cfg.Subtitles.MarginBottom,
	)

	cmd := exec.CommandContext(ctx, "ffmpeg", "-y",
		"-i", videoFile,
		"-vf", subtitleFilter,
		"-c:v", "libx264",
		"-preset", "fast",
		"-crf", "20",
		"-c:a", "copy",
		outFile,
	)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("ffmpeg subtitle burn: %w", err)
	}

	log.Printf("[subtitles] ✅ Subtitles burned: %s", outFile)
	return outFile, nil
}

// ValidateSRT checks that the SRT file is valid and non-empty
func ValidateSRT(srtFile string) error {
	f, err := os.Open(srtFile)
	if err != nil {
		return err
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	lineCount := 0
	for scanner.Scan() {
		lineCount++
	}

	if lineCount < 4 {
		return fmt.Errorf("SRT file appears empty or malformed (%d lines)", lineCount)
	}
	return nil
}

func escapeSubtitlePath(path string) string {
	// FFmpeg subtitle filter needs escaped colons and backslashes
	path = strings.ReplaceAll(path, "\\", "/")
	path = strings.ReplaceAll(path, ":", "\\:")
	return path
}

func boolToInt(b bool) int {
	if b {
		return 1
	}
	return 0
}
