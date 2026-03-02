package collectors

import (
	"context"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
	"gopkg.in/yaml.v3"
)

// CrawlerSource represents a configured web crawler source
type CrawlerSource struct {
	Name      string            `yaml:"name"`
	BaseURL   string            `yaml:"base_url"`
	Enabled   bool              `yaml:"enabled"`
	Interval  int               `yaml:"interval"` // polling interval in minutes
	Rules     []CrawlerRule     `yaml:"rules"`
	Headers   map[string]string `yaml:"headers,omitempty"`
	Delay     int               `yaml:"delay"` // delay between requests in seconds
	UserAgent string            `yaml:"user_agent,omitempty"`
}

// CrawlerRule defines how to extract data from a page
type CrawlerRule struct {
	Name        string `yaml:"name"`
	URLPattern  string `yaml:"url_pattern"`  // pattern to match URLs
	Selector    string `yaml:"selector"`     // CSS selector for items
	TitleSel    string `yaml:"title_sel"`    // CSS selector for title
	LinkSel     string `yaml:"link_sel"`     // CSS selector for link
	DateSel     string `yaml:"date_sel"`     // CSS selector for date
	ContentSel  string `yaml:"content_sel"`  // CSS selector for content
	Description string `yaml:"description"`
}

// CrawledItem represents extracted data from a webpage
type CrawledItem struct {
	Source      string    `json:"source"`
	Title       string    `json:"title"`
	Link        string    `json:"link"`
	Date        string    `json:"date,omitempty"`
	Content     string    `json:"content,omitempty"`
	Description string    `json:"description,omitempty"`
	CrawledAt   time.Time `json:"crawled_at"`
}

// Crawler handles web crawling and data extraction
type Crawler struct {
	client  *http.Client
	sources []CrawlerSource
}

// NewCrawler creates a new web crawler
func NewCrawler(configPath string) (*Crawler, error) {
	sources, err := loadCrawlerSources(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to load crawler sources: %w", err)
	}

	return &Crawler{
		client: &http.Client{
			Timeout: 30 * time.Second,
			CheckRedirect: func(req *http.Request, via []*http.Request) error {
				if len(via) >= 10 {
					return fmt.Errorf("stopped after 10 redirects")
				}
				return nil
			},
		},
		sources: sources,
	}, nil
}

// loadCrawlerSources loads crawler sources from YAML config
func loadCrawlerSources(configPath string) ([]CrawlerSource, error) {
	data, err := loadDataFromYAML(configPath, "crawler")
	if err != nil {
		return nil, err
	}

	var sources []CrawlerSource
	if err := yaml.Unmarshal(data, &sources); err != nil {
		return nil, fmt.Errorf("failed to parse crawler sources: %w", err)
	}

	return sources, nil
}

// CrawlAll crawls all enabled sources
func (c *Crawler) CrawlAll(ctx context.Context) ([]CrawledItem, error) {
	var items []CrawledItem

	for _, source := range c.sources {
		if !source.Enabled {
			continue
		}

		sourceItems, err := c.Crawl(ctx, source)
		if err != nil {
			fmt.Printf("Error crawling %s: %v\n", source.Name, err)
			continue
		}

		items = append(items, sourceItems...)
	}

	return items, nil
}

// Crawl crawls a single source
func (c *Crawler) Crawl(ctx context.Context, source CrawlerSource) ([]CrawledItem, error) {
	var items []CrawledItem

	// Set user agent
	userAgent := source.UserAgent
	if userAgent == "" {
		userAgent = "Mozilla/5.0 (compatible; GlobalIntel Web Crawler)"
	}

	for _, rule := range source.Rules {
		// For now, crawl the base URL
		// In production, you'd discover URLs matching the pattern
		item, err := c.crawlPage(ctx, source.BaseURL, source, rule, userAgent)
		if err != nil {
			fmt.Printf("Error crawling page %s: %v\n", source.BaseURL, err)
			continue
		}

		if item != nil {
			items = append(items, *item)
		}
	}

	return items, nil
}

// crawlPage crawls a single page and extracts data using rules
func (c *Crawler) crawlPage(ctx context.Context, pageURL string, source CrawlerSource, rule CrawlerRule, userAgent string) (*CrawledItem, error) {
	req, err := http.NewRequestWithContext(ctx, "GET", pageURL, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("User-Agent", userAgent)
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")

	// Set custom headers
	for k, v := range source.Headers {
		req.Header.Set(k, v)
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch page: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to parse HTML: %w", err)
	}

	item := &CrawledItem{
		Source:      source.Name,
		Description: rule.Description,
		CrawledAt:   time.Now(),
	}

	// Extract title
	if rule.TitleSel != "" {
		item.Title = strings.TrimSpace(doc.Find(rule.TitleSel).First().Text())
	}

	// Extract link
	if rule.LinkSel != "" {
		link, exists := doc.Find(rule.LinkSel).First().Attr("href")
		if exists {
			// Resolve relative URLs
			baseURL, _ := url.Parse(pageURL)
			linkURL, _ := url.Parse(link)
			item.Link = baseURL.ResolveReference(linkURL).String()
		}
	} else {
		item.Link = pageURL
	}

	// Extract date
	if rule.DateSel != "" {
		item.Date = strings.TrimSpace(doc.Find(rule.DateSel).First().Text())
	}

	// Extract content
	if rule.ContentSel != "" {
		item.Content = strings.TrimSpace(doc.Find(rule.ContentSel).First().Text())
	}

	return item, nil
}

// GetSources returns all configured crawler sources
func (c *Crawler) GetSources() []CrawlerSource {
	return c.sources
}

// AddSource adds a new crawler source
func (c *Crawler) AddSource(source CrawlerSource) {
	c.sources = append(c.sources, source)
}

// RemoveSource removes a crawler source by name
func (c *Crawler) RemoveSource(name string) {
	for i, source := range c.sources {
		if source.Name == name {
			c.sources = append(c.sources[:i], c.sources[i+1:]...)
			return
		}
	}
}

// Helper function to load data from YAML config
func loadDataFromYAML(configPath, section string) ([]byte, error) {
	// This is a placeholder - in production, you'd load from file
	// For now, return empty data
	return []byte{}, nil
}
