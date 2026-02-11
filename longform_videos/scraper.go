package research

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"sort"
	"strings"
	"time"

	"true-crime-pipeline/config"
	"true-crime-pipeline/types"

	"github.com/google/uuid"
)

// hookKeywords boost a story's score when present
var hookKeywords = []string{
	"missing", "murder", "betrayal", "unsolved", "conspiracy",
	"identity", "disappeared", "cold case", "suspect", "arrested",
	"convicted", "escaped", "secret", "revealed", "shocking",
	"victim", "killer", "evidence", "confession", "cover-up",
}

// Scraper holds all scraping dependencies
type Scraper struct {
	cfg        *config.Config
	httpClient *http.Client
	usedStories map[string]bool
}

// New creates a new Scraper
func New(cfg *config.Config) *Scraper {
	return &Scraper{
		cfg:        cfg,
		httpClient: &http.Client{Timeout: 15 * time.Second},
		usedStories: loadUsedStories(cfg.Paths.UsedStoriesLog),
	}
}

// Run fetches, scores, deduplicates and returns the best story
func (s *Scraper) Run(ctx context.Context) (*types.Story, error) {
	log.Println("[research] Starting story scrape...")

	var candidates []*types.Story

	// --- Reddit ---
	redditStories, err := s.scrapeReddit(ctx)
	if err != nil {
		log.Printf("[research] Reddit scrape warning: %v", err)
	} else {
		candidates = append(candidates, redditStories...)
		log.Printf("[research] Reddit: found %d stories", len(redditStories))
	}

	// --- NewsAPI ---
	newsStories, err := s.scrapeNewsAPI(ctx)
	if err != nil {
		log.Printf("[research] NewsAPI scrape warning: %v", err)
	} else {
		candidates = append(candidates, newsStories...)
		log.Printf("[research] NewsAPI: found %d stories", len(newsStories))
	}

	// --- Google News RSS ---
	rssStories, err := s.scrapeGoogleNewsRSS(ctx)
	if err != nil {
		log.Printf("[research] RSS scrape warning: %v", err)
	} else {
		candidates = append(candidates, rssStories...)
		log.Printf("[research] RSS: found %d stories", len(rssStories))
	}

	if len(candidates) == 0 {
		return nil, fmt.Errorf("no stories found from any source")
	}

	// Score and sort
	for _, story := range candidates {
		story.Score = s.scoreStory(story)
	}
	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].Score > candidates[j].Score
	})

	// Pick top non-used story
	for _, story := range candidates {
		if !s.usedStories[story.ID] {
			log.Printf("[research] ✅ Selected story: %q (score: %d)", story.Title, story.Score)
			s.markUsed(story)
			return story, nil
		}
	}

	return nil, fmt.Errorf("all candidate stories have been used already")
}

// --- Reddit scraper ---
func (s *Scraper) scrapeReddit(ctx context.Context) ([]*types.Story, error) {
	clientID := os.Getenv("REDDIT_CLIENT_ID")
	clientSecret := os.Getenv("REDDIT_CLIENT_SECRET")
	userAgent := os.Getenv("REDDIT_USER_AGENT")

	if clientID == "" || clientSecret == "" {
		return nil, fmt.Errorf("REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET not set")
	}

	token, err := s.getRedditToken(clientID, clientSecret, userAgent)
	if err != nil {
		return nil, fmt.Errorf("reddit auth failed: %w", err)
	}

	var stories []*types.Story
	cutoff := time.Now().AddDate(0, 0, -s.cfg.Research.StoryLookbackDays)

	for _, subreddit := range s.cfg.Research.Subreddits {
		posts, err := s.fetchRedditPosts(ctx, subreddit, token, userAgent)
		if err != nil {
			log.Printf("[research] Reddit r/%s error: %v", subreddit, err)
			continue
		}

		for _, post := range posts {
			createdAt := time.Unix(int64(post.Data.Created), 0)
			if createdAt.Before(cutoff) {
				continue
			}
			if post.Data.Score < s.cfg.Research.MinRedditScore {
				continue
			}
			if post.Data.NumComments < s.cfg.Research.MinComments {
				continue
			}

			story := &types.Story{
				ID:          fmt.Sprintf("reddit_%s", post.Data.ID),
				Title:       post.Data.Title,
				Body:        post.Data.Selftext,
				Source:      fmt.Sprintf("r/%s", subreddit),
				SourceURL:   fmt.Sprintf("https://reddit.com%s", post.Data.Permalink),
				PublishedAt: createdAt.Format(time.RFC3339),
				Keywords:    extractKeywords(post.Data.Title + " " + post.Data.Selftext),
			}
			if post.Data.URL != "" && isImageURL(post.Data.URL) {
				story.ImageURLs = append(story.ImageURLs, post.Data.URL)
			}
			stories = append(stories, story)
		}
	}
	return stories, nil
}

type redditTokenResp struct {
	AccessToken string `json:"access_token"`
}

type redditListing struct {
	Data struct {
		Children []struct {
			Data redditPost `json:"data"`
		} `json:"children"`
	} `json:"data"`
}

type redditPost struct {
	ID          string  `json:"id"`
	Title       string  `json:"title"`
	Selftext    string  `json:"selftext"`
	Permalink   string  `json:"permalink"`
	URL         string  `json:"url"`
	Score       int     `json:"score"`
	NumComments int     `json:"num_comments"`
	Created     float64 `json:"created_utc"`
}

func (s *Scraper) getRedditToken(clientID, clientSecret, userAgent string) (string, error) {
	data := url.Values{}
	data.Set("grant_type", "client_credentials")

	req, _ := http.NewRequest("POST", "https://www.reddit.com/api/v1/access_token", strings.NewReader(data.Encode()))
	req.SetBasicAuth(clientID, clientSecret)
	req.Header.Set("User-Agent", userAgent)
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := s.httpClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var tok redditTokenResp
	if err := json.NewDecoder(resp.Body).Decode(&tok); err != nil {
		return "", err
	}
	return tok.AccessToken, nil
}

func (s *Scraper) fetchRedditPosts(ctx context.Context, subreddit, token, userAgent string) ([]struct{ Data redditPost }, error) {
	reqURL := fmt.Sprintf("https://oauth.reddit.com/r/%s/hot?limit=25", subreddit)
	req, _ := http.NewRequestWithContext(ctx, "GET", reqURL, nil)
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("User-Agent", userAgent)

	resp, err := s.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var listing redditListing
	if err := json.NewDecoder(resp.Body).Decode(&listing); err != nil {
		return nil, err
	}
	return listing.Data.Children, nil
}

// --- NewsAPI scraper ---
type newsAPIResponse struct {
	Articles []struct {
		Title       string `json:"title"`
		Description string `json:"description"`
		Content     string `json:"content"`
		URL         string `json:"url"`
		URLToImage  string `json:"urlToImage"`
		PublishedAt string `json:"publishedAt"`
		Source      struct {
			Name string `json:"name"`
		} `json:"source"`
	} `json:"articles"`
}

func (s *Scraper) scrapeNewsAPI(ctx context.Context) ([]*types.Story, error) {
	apiKey := os.Getenv("NEWSAPI_KEY")
	if apiKey == "" {
		return nil, fmt.Errorf("NEWSAPI_KEY not set")
	}

	var stories []*types.Story
	from := time.Now().AddDate(0, 0, -s.cfg.Research.StoryLookbackDays).Format("2006-01-02")

	for _, keyword := range s.cfg.Research.NewsKeywords[:3] { // limit to 3 to save quota
		reqURL := fmt.Sprintf(
			"https://newsapi.org/v2/everything?q=%s&from=%s&sortBy=popularity&language=en&pageSize=10&apiKey=%s",
			url.QueryEscape(keyword), from, apiKey,
		)

		req, _ := http.NewRequestWithContext(ctx, "GET", reqURL, nil)
		resp, err := s.httpClient.Do(req)
		if err != nil {
			continue
		}
		defer resp.Body.Close()

		var result newsAPIResponse
		if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
			continue
		}

		for _, article := range result.Articles {
			if article.Title == "" || article.Title == "[Removed]" {
				continue
			}
			body := article.Description
			if article.Content != "" {
				body = article.Content
			}
			story := &types.Story{
				ID:          fmt.Sprintf("news_%s", uuid.NewString()[:8]),
				Title:       article.Title,
				Body:        body,
				Source:      article.Source.Name,
				SourceURL:   article.URL,
				PublishedAt: article.PublishedAt,
				Keywords:    extractKeywords(article.Title + " " + body),
			}
			if article.URLToImage != "" {
				story.ImageURLs = append(story.ImageURLs, article.URLToImage)
			}
			stories = append(stories, story)
		}
		time.Sleep(200 * time.Millisecond) // be polite to the API
	}
	return stories, nil
}

// --- Google News RSS scraper ---
type rssItem struct {
	Title   string
	Link    string
	PubDate string
}

func (s *Scraper) scrapeGoogleNewsRSS(ctx context.Context) ([]*types.Story, error) {
	var stories []*types.Story

	for _, keyword := range s.cfg.Research.NewsKeywords[:2] {
		feedURL := fmt.Sprintf(
			"https://news.google.com/rss/search?q=%s&hl=en-US&gl=US&ceid=US:en",
			url.QueryEscape(keyword),
		)

		req, _ := http.NewRequestWithContext(ctx, "GET", feedURL, nil)
		req.Header.Set("User-Agent", "Mozilla/5.0 (compatible; TrueCrimePipeline/1.0)")
		resp, err := s.httpClient.Do(req)
		if err != nil {
			continue
		}
		defer resp.Body.Close()

		body, _ := io.ReadAll(resp.Body)
		items := parseRSSItems(string(body))

		for _, item := range items {
			story := &types.Story{
				ID:          fmt.Sprintf("rss_%s", uuid.NewString()[:8]),
				Title:       item.Title,
				Body:        item.Title, // RSS only gives title; body enriched later
				Source:      "Google News RSS",
				SourceURL:   item.Link,
				PublishedAt: item.PubDate,
				Keywords:    extractKeywords(item.Title),
			}
			stories = append(stories, story)
		}
	}
	return stories, nil
}

// parseRSSItems is a lightweight RSS parser (no external deps)
func parseRSSItems(xml string) []rssItem {
	var items []rssItem
	parts := strings.Split(xml, "<item>")
	for _, part := range parts[1:] {
		item := rssItem{
			Title:   extractXMLTag(part, "title"),
			Link:    extractXMLTag(part, "link"),
			PubDate: extractXMLTag(part, "pubDate"),
		}
		if item.Title != "" {
			items = append(items, item)
		}
	}
	return items
}

func extractXMLTag(s, tag string) string {
	open := "<" + tag + ">"
	close := "</" + tag + ">"
	start := strings.Index(s, open)
	if start == -1 {
		return ""
	}
	start += len(open)
	end := strings.Index(s[start:], close)
	if end == -1 {
		return ""
	}
	val := s[start : start+end]
	// strip CDATA
	val = strings.TrimPrefix(val, "<![CDATA[")
	val = strings.TrimSuffix(val, "]]>")
	return strings.TrimSpace(val)
}

// --- Scoring ---
func (s *Scraper) scoreStory(story *types.Story) int {
	score := story.Score // base score from Reddit upvotes

	// Keyword bonus
	titleLower := strings.ToLower(story.Title + " " + story.Body)
	for _, kw := range hookKeywords {
		if strings.Contains(titleLower, kw) {
			score += 50
		}
	}

	// Has image bonus
	if len(story.ImageURLs) > 0 {
		score += 100
	}

	// Recency bonus: published within last 3 days
	if t, err := time.Parse(time.RFC3339, story.PublishedAt); err == nil {
		if time.Since(t) < 72*time.Hour {
			score += 200
		}
	}

	// Body length bonus (more content = better script material)
	if len(story.Body) > 500 {
		score += 75
	}
	if len(story.Body) > 1500 {
		score += 75
	}

	return score
}

// --- Helpers ---
func extractKeywords(text string) []string {
	text = strings.ToLower(text)
	var found []string
	for _, kw := range hookKeywords {
		if strings.Contains(text, kw) {
			found = append(found, kw)
		}
	}
	return found
}

func isImageURL(u string) bool {
	lower := strings.ToLower(u)
	return strings.HasSuffix(lower, ".jpg") ||
		strings.HasSuffix(lower, ".jpeg") ||
		strings.HasSuffix(lower, ".png") ||
		strings.HasSuffix(lower, ".webp")
}

// --- Used stories dedup log ---
func loadUsedStories(path string) map[string]bool {
	used := make(map[string]bool)
	data, err := os.ReadFile(path)
	if err != nil {
		return used
	}
	var ids []string
	if err := json.Unmarshal(data, &ids); err != nil {
		return used
	}
	for _, id := range ids {
		used[id] = true
	}
	return used
}

func (s *Scraper) markUsed(story *types.Story) {
	s.usedStories[story.ID] = true
	var ids []string
	for id := range s.usedStories {
		ids = append(ids, id)
	}
	data, _ := json.MarshalIndent(ids, "", "  ")
	_ = os.WriteFile(s.cfg.Paths.UsedStoriesLog, data, 0644)
}
