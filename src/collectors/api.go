package collectors

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	"gopkg.in/yaml.v3"
)

// APISource represents a configured API source
type APISource struct {
	Name       string            `yaml:"name"`
	BaseURL    string            `yaml:"base_url"`
	Enabled    bool              `yaml:"enabled"`
	Interval   int               `yaml:"interval"` // polling interval in minutes
	AuthType   string            `yaml:"auth_type"` // none, api_key, bearer, oauth
	AuthConfig map[string]string `yaml:"auth_config,omitempty"`
	Endpoints  []APIEndpoint     `yaml:"endpoints"`
}

// APIEndpoint represents a specific API endpoint
type APIEndpoint struct {
	Name        string            `yaml:"name"`
	Path        string            `yaml:"path"`
	Method      string            `yaml:"method"` // GET, POST, etc.
	Params      map[string]string `yaml:"params,omitempty"`
	Headers     map[string]string `yaml:"headers,omitempty"`
	RateLimit   int               `yaml:"rate_limit"` // requests per minute
	Description string            `yaml:"description"`
}

// APIResponse represents a generic API response
type APIResponse struct {
	Data       json.RawMessage `json:"data"`
	Metadata   map[string]any  `json:"metadata,omitempty"`
	StatusCode int             `json:"status_code"`
	Error      string          `json:"error,omitempty"`
}

// APICollector handles API-based data collection
type APICollector struct {
	client  *http.Client
	sources []APISource
}

// NewAPICollector creates a new API collector
func NewAPICollector(configPath string) (*APICollector, error) {
	sources, err := loadAPISources(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to load API sources: %w", err)
	}

	return &APICollector{
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
		sources: sources,
	}, nil
}

// loadAPISources loads API sources from YAML config
func loadAPISources(configPath string) ([]APISource, error) {
	data, err := loadDataFromYAML(configPath, "api")
	if err != nil {
		return nil, err
	}

	var sources []APISource
	if err := yaml.Unmarshal(data, &sources); err != nil {
		return nil, fmt.Errorf("failed to parse API sources: %w", err)
	}

	return sources, nil
}

// FetchAll fetches data from all enabled API sources
func (c *APICollector) FetchAll(ctx context.Context) ([]APIResponse, error) {
	var responses []APIResponse

	for _, source := range c.sources {
		if !source.Enabled {
			continue
		}

		for _, endpoint := range source.Endpoints {
			resp, err := c.Fetch(ctx, source, endpoint)
			if err != nil {
				fmt.Printf("Error fetching %s/%s: %v\n", source.Name, endpoint.Name, err)
				continue
			}

			responses = append(responses, *resp)
		}
	}

	return responses, nil
}

// Fetch fetches data from a specific API endpoint
func (c *APICollector) Fetch(ctx context.Context, source APISource, endpoint APIEndpoint) (*APIResponse, error) {
	urlStr := source.BaseURL + endpoint.Path
	if endpoint.Params != nil {
		u, err := url.Parse(urlStr)
		if err != nil {
			return nil, fmt.Errorf("failed to parse URL: %w", err)
		}

		q := u.Query()
		for k, v := range endpoint.Params {
			q.Set(k, v)
		}
		u.RawQuery = q.Encode()
		urlStr = u.String()
	}

	req, err := http.NewRequestWithContext(ctx, endpoint.Method, urlStr, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set default headers
	req.Header.Set("User-Agent", "Mozilla/5.0 (compatible; GlobalIntel API Collector)")
	req.Header.Set("Accept", "application/json")

	// Set custom headers
	for k, v := range endpoint.Headers {
		req.Header.Set(k, v)
	}

	// Apply authentication
	if err := c.applyAuth(req, source); err != nil {
		return nil, fmt.Errorf("failed to apply auth: %w", err)
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch API: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var response APIResponse
	response.StatusCode = resp.StatusCode

	if err := json.Unmarshal(body, &response.Data); err != nil {
		// If not JSON, store as raw data
		response.Data = json.RawMessage(body)
	}

	if resp.StatusCode >= 400 {
		response.Error = fmt.Sprintf("HTTP %d: %s", resp.StatusCode, string(body))
	}

	return &response, nil
}

// applyAuth applies authentication to the request
func (c *APICollector) applyAuth(req *http.Request, source APISource) error {
	switch source.AuthType {
	case "api_key":
		if key, ok := source.AuthConfig["api_key"]; ok {
			req.Header.Set("X-API-Key", key)
		}
	case "bearer":
		if token, ok := source.AuthConfig["token"]; ok {
			req.Header.Set("Authorization", "Bearer "+token)
		}
	case "oauth":
		// OAuth implementation would go here
		// For now, treat as bearer if token exists
		if token, ok := source.AuthConfig["access_token"]; ok {
			req.Header.Set("Authorization", "Bearer "+token)
		}
	}

	return nil
}

// GetSources returns all configured API sources
func (c *APICollector) GetSources() []APISource {
	return c.sources
}

// AddSource adds a new API source
func (c *APICollector) AddSource(source APISource) {
	c.sources = append(c.sources, source)
}

// RemoveSource removes an API source by name
func (c *APICollector) RemoveSource(name string) {
	for i, source := range c.sources {
		if source.Name == name {
			c.sources = append(c.sources[:i], c.sources[i+1:]...)
			return
		}
	}
}
