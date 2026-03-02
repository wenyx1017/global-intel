"""
Knowledge Graph Validator Module
知识图谱验证接口 - 供大模型调用验证知识
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

from graph import Neo4jGraph, get_graph_connection
from query import KnowledgeGraphQuery, get_query_interface

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeGraphValidator:
    """知识图谱验证器 - 供大模型调用"""
    
    def __init__(self, graph: Optional[Neo4jGraph] = None,
                 query: Optional[KnowledgeGraphQuery] = None):
        """
        初始化验证器
        
        Args:
            graph: Neo4jGraph 实例
            query: KnowledgeGraphQuery 实例
        """
        self.graph = graph or get_graph_connection()
        self.query = query or KnowledgeGraphQuery(self.graph)
    
    def validate_entity_exists(self, name: str, 
                               entity_type: Optional[str] = None) -> Dict[str, Any]:
        """
        验证实体是否存在
        
        Args:
            name: 实体名称
            entity_type: 实体类型（可选）
            
        Returns:
            验证结果
        """
        if entity_type:
            node = self.graph.find_node(entity_type, {"name": name})
        else:
            # 搜索所有类型
            node = self.query.search_by_name(name)
            node = node[0] if node else None
        
        return {
            "exists": node is not None,
            "entity": node,
            "name": name,
            "type": entity_type,
            "timestamp": datetime.now().isoformat()
        }
    
    def validate_relationship(self, entity1: str, entity2: str,
                            rel_type: Optional[str] = None) -> Dict[str, Any]:
        """
        验证两个实体之间是否存在关系
        
        Args:
            entity1: 实体 1 名称
            entity2: 实体 2 名称
            rel_type: 关系类型（可选）
            
        Returns:
            验证结果
        """
        relationships = self.query.query_relationships(
            start_node={"name": entity1},
            end_node={"name": entity2},
            rel_type=rel_type
        )
        
        exists = len(relationships) > 0
        
        return {
            "exists": exists,
            "entity1": entity1,
            "entity2": entity2,
            "relationship_type": rel_type,
            "relationships": relationships,
            "count": len(relationships),
            "timestamp": datetime.now().isoformat()
        }
    
    def validate_entity_type(self, name: str, 
                            expected_type: str) -> Dict[str, Any]:
        """
        验证实体类型是否正确
        
        Args:
            name: 实体名称
            expected_type: 期望的实体类型
            
        Returns:
            验证结果
        """
        node = self.query.search_by_name(name)
        
        if not node:
            return {
                "valid": False,
                "reason": "实体不存在",
                "name": name,
                "expected_type": expected_type
            }
        
        node_obj = node[0] if isinstance(node, list) else node
        actual_types = node_obj.get('labels', [])
        
        is_valid = expected_type in actual_types
        
        return {
            "valid": is_valid,
            "name": name,
            "expected_type": expected_type,
            "actual_types": actual_types,
            "entity": node_obj,
            "timestamp": datetime.now().isoformat()
        }
    
    def validate_policy_chain(self, policy_name: str) -> Dict[str, Any]:
        """
        验证政策影响链的完整性
        
        Args:
            policy_name: 政策名称
            
        Returns:
            验证结果
        """
        chain = self.query.get_policy_chain(policy_name)
        
        if "error" in chain:
            return {
                "valid": False,
                "reason": chain["error"],
                "policy": policy_name
            }
        
        has_issuer = len(chain.get('issuers', [])) > 0
        has_affected = len(chain.get('affected_by', [])) > 0
        
        return {
            "valid": True,
            "policy": policy_name,
            "has_issuer": has_issuer,
            "has_affected_entities": has_affected,
            "issuer_count": len(chain.get('issuers', [])),
            "affected_count": len(chain.get('affected_by', [])),
            "chain": chain,
            "timestamp": datetime.now().isoformat()
        }
    
    def validate_org_network(self, org_name: str) -> Dict[str, Any]:
        """
        验证组织关联网络的完整性
        
        Args:
            org_name: 组织名称
            
        Returns:
            验证结果
        """
        network = self.query.get_org_connections(org_name)
        
        if "error" in network:
            return {
                "valid": False,
                "reason": network.get("error", "未知错误"),
                "organization": org_name
            }
        
        return {
            "valid": True,
            "organization": org_name,
            "connection_count": network.get("count", 0),
            "has_connections": network.get("count", 0) > 0,
            "network": network,
            "timestamp": datetime.now().isoformat()
        }
    
    def find_missing_relationships(self, entity1: str, entity2: str,
                                   expected_rel: str) -> Dict[str, Any]:
        """
        查找缺失的关系
        
        Args:
            entity1: 实体 1 名称
            entity2: 实体 2 名称
            expected_rel: 期望的关系类型
            
        Returns:
            验证结果
        """
        existing = self.validate_relationship(entity1, entity2, expected_rel)
        
        return {
            "missing": not existing["exists"],
            "entity1": entity1,
            "entity2": entity2,
            "expected_relationship": expected_rel,
            "existing_relationships": existing.get("relationships", []),
            "suggestion": f"需要创建关系：{entity1} -[{expected_rel}]-> {entity2}" if not existing["exists"] else "关系已存在",
            "timestamp": datetime.now().isoformat()
        }
    
    def validate_data_quality(self) -> Dict[str, Any]:
        """
        验证数据质量
        
        Returns:
            数据质量报告
        """
        stats = self.query.get_statistics()
        
        issues = []
        warnings = []
        
        # 检查孤立节点
        orphan_query = """
        MATCH (n)
        WHERE NOT (n)--()
        RETURN n
        """
        orphans = self.graph.execute_query(orphan_query)
        
        if len(orphans) > 0:
            warnings.append({
                "type": "orphan_nodes",
                "count": len(orphans),
                "message": f"发现 {len(orphans)} 个孤立节点"
            })
        
        # 检查缺少必要属性的节点
        for label in ['GPE', 'GOV_ORG', 'ORG', 'PERSON', 'EVENT', 'LAW_POLICY']:
            missing_name_query = f"""
            MATCH (n:{label})
            WHERE n.name IS NULL OR n.name = ''
            RETURN count(n) as count
            """
            result = self.graph.execute_query(missing_name_query)
            count = result[0]['count'] if result else 0
            
            if count > 0:
                issues.append({
                    "type": "missing_name",
                    "label": label,
                    "count": count,
                    "message": f"{label} 类型有 {count} 个节点缺少 name 属性"
                })
        
        # 计算质量分数
        total_nodes = stats['total_nodes']
        issue_count = len(issues)
        warning_count = len(warnings)
        
        quality_score = 100
        quality_score -= issue_count * 10
        quality_score -= warning_count * 2
        quality_score = max(0, quality_score)
        
        return {
            "quality_score": quality_score,
            "total_nodes": total_nodes,
            "total_relationships": stats['total_relationships'],
            "issues": issues,
            "warnings": warnings,
            "nodes_by_type": stats['nodes_by_type'],
            "timestamp": datetime.now().isoformat()
        }
    
    def validate_consistency(self, entity_name: str) -> Dict[str, Any]:
        """
        验证实体数据一致性
        
        Args:
            entity_name: 实体名称
            
        Returns:
            一致性验证结果
        """
        nodes = self.query.search_by_name(entity_name)
        
        if len(nodes) == 0:
            return {
                "consistent": True,
                "reason": "实体不存在",
                "entity": entity_name
            }
        
        if len(nodes) == 1:
            return {
                "consistent": True,
                "reason": "唯一实体",
                "entity": entity_name,
                "node": nodes[0]
            }
        
        # 检查是否有重复
        types_count = {}
        for node in nodes:
            node_type = str(node.get('labels', ['UNKNOWN'])[0])
            types_count[node_type] = types_count.get(node_type, 0) + 1
        
        duplicates = {k: v for k, v in types_count.items() if v > 1}
        
        return {
            "consistent": len(duplicates) == 0,
            "entity": entity_name,
            "duplicate_count": len(nodes),
            "duplicates_by_type": duplicates,
            "nodes": nodes,
            "suggestion": "可能存在重复实体，建议合并" if duplicates else "多个不同类型的同名实体",
            "timestamp": datetime.now().isoformat()
        }
    
    def batch_validate(self, entities: List[Dict]) -> List[Dict]:
        """
        批量验证实体
        
        Args:
            entities: 实体列表，每个实体包含 name 和 type
            
        Returns:
            验证结果列表
        """
        results = []
        
        for entity in entities:
            name = entity.get('name')
            entity_type = entity.get('type')
            
            if not name:
                results.append({
                    "valid": False,
                    "error": "缺少 name 字段",
                    "input": entity
                })
                continue
            
            result = self.validate_entity_exists(name, entity_type)
            results.append(result)
        
        return results
    
    def get_validation_report(self) -> Dict[str, Any]:
        """
        生成完整的验证报告
        
        Returns:
            验证报告
        """
        stats = self.query.get_statistics()
        quality = self.validate_data_quality()
        
        return {
            "summary": {
                "total_nodes": stats['total_nodes'],
                "total_relationships": stats['total_relationships'],
                "quality_score": quality['quality_score']
            },
            "nodes_by_type": stats['nodes_by_type'],
            "relationships_by_type": stats['relationships_by_type'],
            "data_quality": quality,
            "generated_at": datetime.now().isoformat()
        }
    
    def close(self):
        """关闭连接"""
        if self.graph:
            self.graph.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# LLM 调用接口
def validate_entity(name: str, entity_type: Optional[str] = None) -> Dict:
    """
    LLM 调用接口：验证实体存在性
    
    Args:
        name: 实体名称
        entity_type: 实体类型
        
    Returns:
        验证结果
    """
    with KnowledgeGraphValidator() as validator:
        return validator.validate_entity_exists(name, entity_type)


def validate_relationship_llm(entity1: str, entity2: str,
                             rel_type: Optional[str] = None) -> Dict:
    """
    LLM 调用接口：验证关系
    
    Args:
        entity1: 实体 1
        entity2: 实体 2
        rel_type: 关系类型
        
    Returns:
        验证结果
    """
    with KnowledgeGraphValidator() as validator:
        return validator.validate_relationship(entity1, entity2, rel_type)


def get_validation_report() -> Dict:
    """
    LLM 调用接口：获取验证报告
    
    Returns:
        验证报告
    """
    with KnowledgeGraphValidator() as validator:
        return validator.get_validation_report()


# 便捷函数
def get_validator() -> KnowledgeGraphValidator:
    """获取验证器实例"""
    return KnowledgeGraphValidator()


if __name__ == "__main__":
    # 测试验证器
    with get_validator() as validator:
        print("验证报告:", validator.get_validation_report())
        
        # 测试实体验证
        result = validator.validate_entity_exists("中国", "GPE")
        print("实体验证:", result)
