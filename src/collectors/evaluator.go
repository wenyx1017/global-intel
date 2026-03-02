package collectors

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os/exec"
	"path/filepath"
	"time"
)

// SourceScore 信源评分结果
type SourceScore struct {
	SourceID     string  `json:"source_id"`
	Accuracy     float64 `json:"accuracy"`
	Authenticity float64 `json:"authenticity"`
	Objectivity  float64 `json:"objectivity"`
	Importance   float64 `json:"importance"`
	TotalScore   float64 `json:"total_score"`
	Grade        string  `json:"grade"`
	EvaluatedAt  string  `json:"evaluated_at"`
}

// SourceInfo 信源基本信息
type SourceInfo struct {
	Domain          string `json:"domain"`
	Author          string `json:"author"`
	Citations       int    `json:"citations"`
	EstablishedDate string `json:"established_date,omitempty"`
}

// Article 文章信息
type Article struct {
	ID          string    `json:"id"`
	Title       string    `json:"title"`
	Content     string    `json:"content"`
	PublishedAt time.Time `json:"published_at"`
	Citations   int       `json:"citations"`
	Views       int       `json:"views"`
	Shares      int       `json:"shares"`
}

// SourceData 评价用信源数据
type SourceData struct {
	SourceID    string    `json:"source_id"`
	SourceInfo  SourceInfo `json:"source_info"`
	Articles    []Article `json:"articles"`
}

// EvaluatorResult 评价结果
type EvaluatorResult struct {
	SourceID     string
	TotalScore   float64
	Grade        string
	Accuracy     float64
	Authenticity float64
	Objectivity  float64
	Importance   float64
}

// SourceEvaluator Python 评价器接口
type SourceEvaluator struct {
	pythonPath string
	scriptPath string
	dbPath     string
}

// NewSourceEvaluator 创建评价器实例
func NewSourceEvaluator(pythonPath, scriptDir, dbPath string) *SourceEvaluator {
	if pythonPath == "" {
		pythonPath = "python3"
	}
	if dbPath == "" {
		dbPath = "source_evaluations.db"
	}
	
	return &SourceEvaluator{
		pythonPath: pythonPath,
		scriptPath: filepath.Join(scriptDir, "evaluator.py"),
		dbPath:     dbPath,
	}
}

// EvaluateSource 评价单个信源
func (e *SourceEvaluator) EvaluateSource(sourceData SourceData) (*EvaluatorResult, error) {
	// 准备输入数据
	inputData := []SourceData{sourceData}
	jsonData, err := json.Marshal(inputData)
	if err != nil {
		return nil, fmt.Errorf("序列化数据失败：%w", err)
	}

	// 创建 Python 脚本
	script := fmt.Sprintf(`
import sys
import json
sys.path.insert(0, '%s')

from evaluator import quick_evaluate

data = json.loads('%s')
results = quick_evaluate(data, db_path='%s')
print(json.dumps(results[0]))
`, filepath.Dir(e.scriptPath), string(jsonData), e.dbPath)

	// 执行 Python 脚本
	cmd := exec.Command(e.pythonPath, "-c", script)
	var out bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &out
	
	err = cmd.Run()
	if err != nil {
		return nil, fmt.Errorf("执行评价脚本失败：%w, 输出：%s", err, out.String())
	}

	// 解析结果
	var score SourceScore
	err = json.Unmarshal(out.Bytes(), &score)
	if err != nil {
		return nil, fmt.Errorf("解析结果失败：%w", err)
	}

	return &EvaluatorResult{
		SourceID:     score.SourceID,
		TotalScore:   score.TotalScore,
		Grade:        score.Grade,
		Accuracy:     score.Accuracy,
		Authenticity: score.Authenticity,
		Objectivity:  score.Objectivity,
		Importance:   score.Importance,
	}, nil
}

// EvaluateMultipleSources 批量评价多个信源
func (e *SourceEvaluator) EvaluateMultipleSources(sourcesData []SourceData) ([]EvaluatorResult, error) {
	jsonData, err := json.Marshal(sourcesData)
	if err != nil {
		return nil, fmt.Errorf("序列化数据失败：%w", err)
	}

	// 创建 Python 脚本
	script := fmt.Sprintf(`
import sys
import json
sys.path.insert(0, '%s')

from evaluator import quick_evaluate

data = json.loads('%s')
results = quick_evaluate(data, db_path='%s')
print(json.dumps(results))
`, filepath.Dir(e.scriptPath), string(jsonData), e.dbPath)

	// 执行 Python 脚本
	cmd := exec.Command(e.pythonPath, "-c", script)
	var out bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &out
	
	err = cmd.Run()
	if err != nil {
		return nil, fmt.Errorf("执行评价脚本失败：%w, 输出：%s", err, out.String())
	}

	// 解析结果
	var scores []SourceScore
	err = json.Unmarshal(out.Bytes(), &scores)
	if err != nil {
		return nil, fmt.Errorf("解析结果失败：%w", err)
	}

	results := make([]EvaluatorResult, len(scores))
	for i, score := range scores {
		results[i] = EvaluatorResult{
			SourceID:     score.SourceID,
			TotalScore:   score.TotalScore,
			Grade:        score.Grade,
			Accuracy:     score.Accuracy,
			Authenticity: score.Authenticity,
			Objectivity:  score.Objectivity,
			Importance:   score.Importance,
		}
	}

	return results, nil
}

// ShouldEliminate 检查信源是否应该被淘汰
func (e *SourceEvaluator) ShouldEliminate(sourceID string) (bool, error) {
	script := fmt.Sprintf(`
import sys
import json
sys.path.insert(0, '%s')

from evaluator import SourceEvaluator

evaluator = SourceEvaluator(db_path='%s')
candidates = evaluator.get_elimination_candidates()
eliminated = [s for s in candidates if s['source_id'] == '%s']
print(json.dumps(len(eliminated) > 0))
`, filepath.Dir(e.scriptPath), e.dbPath, sourceID)

	cmd := exec.Command(e.pythonPath, "-c", script)
	var out bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &out
	
	err := cmd.Run()
	if err != nil {
		return false, fmt.Errorf("检查淘汰状态失败：%w", err)
	}

	var shouldEliminate bool
	err = json.Unmarshal(out.Bytes(), &shouldEliminate)
	if err != nil {
		return false, fmt.Errorf("解析结果失败：%w", err)
	}

	return shouldEliminate, nil
}

// GetSourceGrade 获取信源等级
func (e *SourceEvaluator) GetSourceGrade(sourceID string) (string, error) {
	script := fmt.Sprintf(`
import sys
sys.path.insert(0, '%s')

from evaluator import SourceEvaluator

evaluator = SourceEvaluator(db_path='%s')
grade = evaluator.get_source_grade('%s')
print(grade if grade else '')
`, filepath.Dir(e.scriptPath), e.dbPath, sourceID)

	cmd := exec.Command(e.pythonPath, "-c", script)
	var out bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &out
	
	err := cmd.Run()
	if err != nil {
		return "", fmt.Errorf("获取信源等级失败：%w", err)
	}

	return out.String(), nil
}

// GenerateReport 生成评价报告
func (e *SourceEvaluator) GenerateReport() (map[string]interface{}, error) {
	script := fmt.Sprintf(`
import sys
import json
sys.path.insert(0, '%s')

from evaluator import SourceEvaluator

evaluator = SourceEvaluator(db_path='%s')
report = evaluator.generate_report()
print(json.dumps(report))
`, filepath.Dir(e.scriptPath), e.dbPath)

	cmd := exec.Command(e.pythonPath, "-c", script)
	var out bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &out
	
	err := cmd.Run()
	if err != nil {
		return nil, fmt.Errorf("生成报告失败：%w", err)
	}

	var report map[string]interface{}
	err = json.Unmarshal(out.Bytes(), &report)
	if err != nil {
		return nil, fmt.Errorf("解析报告失败：%w", err)
	}

	return report, nil
}
