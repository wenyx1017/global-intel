module global-intel

// 全球情报系统 - Go 模块配置
// Global Intelligence System - Go Module Configuration
// 最后更新：2026-03-02

go 1.21

require (
	// RSS 解析
	github.com/mmcdole/gofeed v1.3.0
	
	// HTTP 客户端
	github.com/go-resty/resty/v2 v2.11.0
	
	// HTML 解析（爬虫）
	github.com/PuerkitoBio/goquery v1.8.1
	
	// Cron 调度
	github.com/robfig/cron/v3 v3.0.1
	
	// YAML 配置
	gopkg.in/yaml.v3 v3.0.1
	
	// 日志
	go.uber.org/zap v1.26.0
	
	// 数据库
	github.com/mattn/go-sqlite3 v1.14.18
	github.com/jmoiron/sqlx v1.3.5
	
	// Neo4j 图数据库
	github.com/neo4j/neo4j-go-driver/v5 v5.14.0
	
	// Redis 缓存
	github.com/redis/go-redis/v9 v9.3.0
	
	// 并发控制
	golang.org/x/sync v0.5.0
	
	// 配置管理
	github.com/spf13/viper v1.18.0
	
	// 测试
	github.com/stretchr/testify v1.8.4
)

require (
	// 间接依赖
	github.com/andybalholm/cascadia v1.3.2 // indirect
	github.com/json-iterator/go v1.1.12 // indirect
	github.com/modern-go/concurrent v0.0.0-20180306012644-bacd9c7ef1dd // indirect
	github.com/modern-go/reflect2 v1.0.2 // indirect
	golang.org/x/net v0.19.0 // indirect
	gopkg.in/yaml.v2 v2.4.0 // indirect
)
