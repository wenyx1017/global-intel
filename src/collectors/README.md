# 数据采集器 (Data Collectors)

Global Intel 项目的数据采集模块，支持 RSS 订阅、官方 API 接入和网页爬虫。

## 功能模块

### 1. RSS 采集器 (rss.go)
- 支持 RSS 2.0 和 Atom 格式
- 可配置轮询间隔
- 自动解析 feed 元数据和条目

### 2. API 采集器 (api.go)
- 支持多种认证方式 (API Key, Bearer Token, OAuth)
- 可配置自定义请求头和参数
- 支持速率限制

### 3. 网页爬虫 (crawler.go)
- 基于 CSS 选择器的数据提取
- 可配置爬取规则
- 支持自定义 User-Agent 和请求延迟

## 快速开始

### 初始化模块
```bash
cd /home/wenyx/.openclaw/workspace/global-intel/src/collectors
go mod tidy
```

### 使用示例

```go
package main

import (
    "context"
    "fmt"
    "global-intel/collectors"
)

func main() {
    ctx := context.Background()
    
    // RSS 采集
    rssCollector, err := collectors.NewRSSCollector("sources.yaml")
    if err != nil {
        panic(err)
    }
    feeds, err := rssCollector.FetchAll(ctx)
    if err != nil {
        panic(err)
    }
    for _, feed := range feeds {
        fmt.Printf("Feed: %s, Items: %d\n", feed.Title, len(feed.Items))
    }
    
    // API 采集
    apiCollector, err := collectors.NewAPICollector("sources.yaml")
    if err != nil {
        panic(err)
    }
    responses, err := apiCollector.FetchAll(ctx)
    if err != nil {
        panic(err)
    }
    for _, resp := range responses {
        fmt.Printf("Status: %d, Data: %s\n", resp.StatusCode, string(resp.Data))
    }
    
    // 网页爬虫
    crawler, err := collectors.NewCrawler("sources.yaml")
    if err != nil {
        panic(err)
    }
    items, err := crawler.CrawlAll(ctx)
    if err != nil {
        panic(err)
    }
    for _, item := range items {
        fmt.Printf("Source: %s, Title: %s, Link: %s\n", item.Source, item.Title, item.Link)
    }
}
```

## 配置说明

配置文件 `sources.yaml` 包含三个主要部分:

### RSS 配置
```yaml
rss:
  - name: "源名称"
    url: "https://example.com/feed.xml"
    enabled: true
    interval: 30  # 轮询间隔 (分钟)
```

### API 配置
```yaml
api:
  - name: "API 名称"
    base_url: "https://api.example.com"
    enabled: true
    interval: 60
    auth_type: "api_key"  # none, api_key, bearer, oauth
    auth_config:
      api_key: "your-api-key"
    endpoints:
      - name: "端点名称"
        path: "/v1/data"
        method: GET
        description: "端点描述"
```

### 爬虫配置
```yaml
crawler:
  - name: "网站名称"
    base_url: "https://example.com"
    enabled: true
    interval: 60
    delay: 5  # 请求延迟 (秒)
    rules:
      - name: "规则名称"
        url_pattern: "/news/"
        selector: ".news-item"
        title_sel: "h2 a"
        link_sel: "h2 a"
        date_sel: ".date"
        description: "规则描述"
```

## 初始信源

### 中国 (5 个)
- gov.cn (中国政府网)
- xinhuanet.com (新华社)
- pbc.gov.cn (央行)
- stats.gov.cn (统计局)
- csrc.gov.cn (证监会)

### 全球 (5 个)
- whitehouse.gov (白宫)
- imf.org (IMF)
- worldbank.org (世行)
- sec.gov (美国证监会)
- reuters.com (路透)

## 注意事项

1. **API 认证**: 部分 API 需要 API Key，请在环境变量中设置
2. **爬取频率**: 请遵守目标网站的 robots.txt 和速率限制
3. **错误处理**: 所有采集器都会跳过失败的源并继续处理其他源
4. **上下文取消**: 所有采集方法都支持 context 取消，可用于优雅关闭

## 扩展

添加新信源只需在 `sources.yaml` 中添加配置，无需修改代码。
