package collectors

import (
	"context"
	"encoding/xml"
	"fmt"
	"io"
	"net/http"
	"time"

	"gopkg.in/yaml.v3"
)

// RSSItem represents a single RSS feed item
type RSSItem struct {
	Title       string `xml:"channel>item>title"`
	Link        string `xml:"channel>item>link"`
	Description string `xml:"channel>item>description"`
	PubDate     string `xml:"channel>item>pubDate"`
	GUID        string `xml:"channel>item>guid"`
	Author      string `xml:"channel>item>author"`
}

// RSSFeed represents a parsed RSS feed
type RSSFeed struct {
	Title       string    `xml:"channel>title"`
	Link        string    `xml:"channel>link"`
	Description string    `xml:"channel>description"`
	Items       []RSSItem `xml:"channel>item"`
}

// RSSSource represents a configured RSS source
type RSSSource struct {
	Name     string `yaml:"name"`
	URL      string `yaml:"url"`
	Enabled  bool   `yaml:"enabled"`
	Interval int    `yaml:"interval"` // polling interval in minutes
}

// RSSCollector handles RSS feed collection
type RSSCollector struct {
	client  *http.Client
	sources []RSSSource
}

// NewRSSCollector creates a new RSS collector
func NewRSSCollector(configPath string) (*RSSCollector, error) {
	sources, err := loadRSSSources(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to load RSS sources: %w", err)
	}

	return &RSSCollector{
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
		sources: sources,
	}, nil
}

// loadRSSSources loads RSS sources from YAML config
func loadRSSSources(configPath string) ([]RSSSource, error) {
	data, err := loadDataFromYAML(configPath, "rss")
	if err != nil {
		return nil, err
	}

	var sources []RSSSource
	if err := yaml.Unmarshal(data, &sources); err != nil {
		return nil, fmt.Errorf("failed to parse RSS sources: %w", err)
	}

	return sources, nil
}

// FetchAll fetches RSS feeds from all enabled sources
func (c *RSSCollector) FetchAll(ctx context.Context) ([]RSSFeed, error) {
	var feeds []RSSFeed

	for _, source := range c.sources {
		if !source.Enabled {
			continue
		}

		feed, err := c.Fetch(ctx, source.URL)
		if err != nil {
			fmt.Printf("Error fetching %s: %v\n", source.Name, err)
			continue
		}

		feeds = append(feeds, *feed)
	}

	return feeds, nil
}

// Fetch fetches and parses a single RSS feed
func (c *RSSCollector) Fetch(ctx context.Context, url string) (*RSSFeed, error) {
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("User-Agent", "Mozilla/5.0 (compatible; GlobalIntel RSS Collector)")

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch feed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var feed RSSFeed
	if err := xml.Unmarshal(body, &feed); err != nil {
		return nil, fmt.Errorf("failed to parse RSS: %w", err)
	}

	return &feed, nil
}

// GetSources returns all configured RSS sources
func (c *RSSCollector) GetSources() []RSSSource {
	return c.sources
}

// AddSource adds a new RSS source
func (c *RSSCollector) AddSource(source RSSSource) {
	c.sources = append(c.sources, source)
}

// RemoveSource removes an RSS source by URL
func (c *RSSCollector) RemoveSource(url string) {
	for i, source := range c.sources {
		if source.URL == url {
			c.sources = append(c.sources[:i], c.sources[i+1:]...)
			return
		}
	}
}
