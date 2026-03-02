package collectors

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/mmcdole/gofeed"
)

// RSSCollector RSS 采集器
type RSSCollector struct {
	config     RSSConfig
	parser     *gofeed.Parser
	httpClient *gofeed.HTTPClient
	mu         sync.RWMutex
}

// RSSConfig RSS 配置
type RSSConfig struct {
	URL            string        `yaml:"url"`
	Name           string        `yaml:"name"`
	Category       string        `yaml:"category"`
	UpdateInterval time.Duration `yaml:"update_interval"`
	Timeout        time.Duration `yaml:"timeout"`
	RetryCount     int           `yaml:"retry"`
}

// RSSItem RSS 条目
type RSSItem struct {
	ID          string    `json:"id"`
	Title       string    `json:"title"`
	Description string    `json:"description"`
	Link        string    `json:"link"`
	PubDate     time.Time `json:"pub_date"`
	Source      string    `json:"source"`
	Category    string    `json:"category"`
	Language    string    `json:"language"`
	CollectedAt time.Time `json:"collected_at"`
}

// NewRSSCollector 创建 RSS 采集器
func NewRSSCollector(config RSSConfig) *RSSCollector {
	parser := gofeed.NewParser()
	parser.UserAgent = "GlobalIntelBot/0.1"

	return &RSSCollector{
		config: config,
		parser: parser,
		httpClient: &gofeed.HTTPClient{
			ConnectTimeout: 10 * time.Second,
			ReadTimeout:    30 * time.Second,
		},
	}
}

// Collect 采集 RSS 数据
func (c *RSSCollector) Collect(ctx context.Context) ([]*RSSItem, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()

	log.Printf("开始采集 RSS: %s (%s)", c.config.Name, c.config.URL)

	// 创建带超时的上下文
	timeoutCtx, cancel := context.WithTimeout(ctx, c.config.Timeout)
	defer cancel()

	// 获取 RSS Feed
	feed, err := c.parser.ParseURLWithContext(c.config.URL, timeoutCtx)
	if err != nil {
		return nil, fmt.Errorf("解析 RSS 失败：%w", err)
	}

	// 转换为内部格式
	items := make([]*RSSItem, 0, len(feed.Items))
	for _, item := range feed.Items {
		rssItem := &RSSItem{
			ID:          item.GUID,
			Title:       item.Title,
			Description: item.Description,
			Link:        item.Link,
			PubDate:     *item.PublishedParsed,
			Source:      c.config.Name,
			Category:    c.config.Category,
			Language:    feed.Language,
			CollectedAt: time.Now(),
		}
		items = append(items, rssItem)
	}

	log.Printf("采集完成：%s, 获取 %d 条记录", c.config.Name, len(items))
	return items, nil
}

// CollectWithRetry 带重试的采集
func (c *RSSCollector) CollectWithRetry(ctx context.Context) ([]*RSSItem, error) {
	var lastErr error

	for attempt := 0; attempt < c.config.RetryCount; attempt++ {
		items, err := c.Collect(ctx)
		if err == nil {
			return items, nil
		}

		lastErr = err
		log.Printf("采集失败 (尝试 %d/%d): %v", attempt+1, c.config.RetryCount, err)

		if attempt < c.config.RetryCount-1 {
			time.Sleep(time.Second * time.Duration(attempt+1))
		}
	}

	return nil, fmt.Errorf("采集失败，已重试 %d 次：%w", c.config.RetryCount, lastErr)
}

// Validate 验证 RSS Feed 是否有效
func (c *RSSCollector) Validate(ctx context.Context) error {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	feed, err := c.parser.ParseURLWithContext(c.config.URL, ctx)
	if err != nil {
		return fmt.Errorf("验证失败：%w", err)
	}

	if feed == nil || len(feed.Items) == 0 {
		return fmt.Errorf("RSS Feed 为空")
	}

	log.Printf("验证成功：%s, 共 %d 条记录", c.config.Name, len(feed.Items))
	return nil
}

// GetUpdateInterval 获取更新间隔
func (c *RSSCollector) GetUpdateInterval() time.Duration {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.config.UpdateInterval
}

// UpdateConfig 更新配置
func (c *RSSCollector) UpdateConfig(config RSSConfig) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.config = config
}

// RSSCollectorManager RSS 采集器管理器
type RSSCollectorManager struct {
	collectors map[string]*RSSCollector
	mu         sync.RWMutex
}

// NewRSSCollectorManager 创建管理器
func NewRSSCollectorManager() *RSSCollectorManager {
	return &RSSCollectorManager{
		collectors: make(map[string]*RSSCollector),
	}
}

// AddCollector 添加采集器
func (m *RSSCollectorManager) AddCollector(id string, config RSSConfig) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.collectors[id] = NewRSSCollector(config)
	log.Printf("添加 RSS 采集器：%s", id)
}

// RemoveCollector 移除采集器
func (m *RSSCollectorManager) RemoveCollector(id string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.collectors, id)
	log.Printf("移除 RSS 采集器：%s", id)
}

// CollectAll 采集所有 RSS
func (m *RSSCollectorManager) CollectAll(ctx context.Context) (map[string][]*RSSItem, error) {
	m.mu.RLock()
	collectors := make([]*RSSCollector, 0, len(m.collectors))
	for _, c := range m.collectors {
		collectors = append(collectors, c)
	}
	m.mu.RUnlock()

	results := make(map[string][]*RSSItem)
	var wg sync.WaitGroup
	var mu sync.Mutex
	var errs []error

	for _, collector := range collectors {
		wg.Add(1)
		go func(c *RSSCollector) {
			defer wg.Done()
			items, err := c.CollectWithRetry(ctx)
			mu.Lock()
			defer mu.Unlock()
			if err != nil {
				errs = append(errs, err)
			} else {
				results[c.config.Name] = items
			}
		}(collector)
	}

	wg.Wait()

	if len(errs) > 0 {
		log.Printf("部分采集失败：%d 个错误", len(errs))
	}

	return results, nil
}
