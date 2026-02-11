#!/bin/bash
# ============================================================
# TRUE CRIME PIPELINE — ONE COMMAND SETUP
# Run: chmod +x setup.sh && ./setup.sh
# ============================================================

echo "🎬 Setting up True Crime Auto-YouTube Pipeline..."
echo ""

# --- Check Python version ---
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED="3.10"
if python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)"; then
  echo "✅ Python $PYTHON_VERSION detected"
else
  echo "❌ Python 3.10+ required. You have $PYTHON_VERSION"
  echo "   Install from https://python.org"
  exit 1
fi

# --- Install FFmpeg (system dependency) ---
echo ""
echo "📦 Installing FFmpeg..."
if command -v ffmpeg &> /dev/null; then
  echo "✅ FFmpeg already installed"
else
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo apt-get update -qq && sudo apt-get install -y ffmpeg
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    brew install ffmpeg
  else
    echo "⚠️  Windows detected — install FFmpeg manually from https://ffmpeg.org/download.html"
    echo "   Then add it to your PATH"
  fi
fi

# --- Create virtual environment ---
echo ""
echo "🐍 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "✅ Virtual environment created and activated"

# --- Upgrade pip ---
pip install --upgrade pip -q

# --- Install Python dependencies ---
echo ""
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# --- Install Whisper model (base) ---
echo ""
echo "🎤 Downloading Whisper base model..."
python3 -c "import whisper; whisper.load_model('base')"
echo "✅ Whisper base model ready"

# --- Create folder structure ---
echo ""
echo "📁 Creating folder structure..."
mkdir -p assets/video
mkdir -p assets/sfx
mkdir -p output
mkdir -p logs

# --- Create empty usage log ---
echo "{}" > assets/video/usage_log.json
echo "[]" > logs/used_stories.json

# --- Create .env template ---
if [ ! -f .env ]; then
  echo ""
  echo "🔑 Creating .env template..."
  cat > .env << 'EOF'
# Copy this file and fill in your keys
# For GitHub Actions, add these as repository Secrets instead

GROQ_API_KEY=your_groq_api_key_here
NEWSAPI_KEY=your_newsapi_key_here
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
REDDIT_USER_AGENT=TrueCrimePipeline/1.0
SERPAPI_KEY=your_serpapi_key_here
YOUTUBE_CLIENT_ID=your_youtube_client_id_here
YOUTUBE_CLIENT_SECRET=your_youtube_client_secret_here
YOUTUBE_REFRESH_TOKEN=your_youtube_refresh_token_here
EOF
  echo "✅ .env template created — fill in your API keys"
fi

# --- Check assets ---
echo ""
VIDEO_COUNT=$(ls assets/video/*.mp4 2>/dev/null | wc -l)
if [ "$VIDEO_COUNT" -eq 0 ]; then
  echo "⚠️  No video clips found in assets/video/"
  echo "   Add your crime b-roll .mp4 clips there and fill in assets/video/tags.json"
else
  echo "✅ Found $VIDEO_COUNT video clip(s) in assets/video/"
fi

echo ""
echo "============================================"
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Fill in your API keys in .env"
echo "  2. Add video clips to assets/video/"
echo "  3. Tag your clips in assets/video/tags.json"
echo "  4. Run: python pipeline.py (manual test)"
echo "  5. Push to GitHub for auto Tuesday/Friday uploads"
echo "============================================"
