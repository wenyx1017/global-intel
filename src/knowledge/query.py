"""
Knowledge Graph Query Module
知识图谱查询接口 - 提供多种查询方式
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import logging

from graph import Neo4jGraph, get_graph_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeGraphQuery:
    """知识图谱查询接口"""
    
    def __init__(self, graph: Optional[Neo4jGraph] = None):
        """
        初始化查询接口
        
        Args:
            graph: Neo4jGraph 实例
        """
        self.graph = graph or get_graph_connection()
    
    def search_by_name(self, name: str, 
                       labels: Optional[List[str]] = None) -> List[Dict]:
        """
        按名称搜索节点
        
        Args:
            name: 名称（支持模糊匹配）
            labels: 限制的标签列表
            
        Returns:
            匹配的节点列表
        """
        if labels:
            label_pattern = "|".join([f":{label}" for label in labels])
            query = f"""
            MATCH (n{label_pattern})
            WHERE n.name CONTAINS $name
            RETURN n
            ORDER BY n.name
            """
        else:
            query = """
            MATCH (n)
            WHERE n.name CONTAINS $name
            RETURN n
            ORDER BY labels(n), n.name
            """
        
        results = self.graph.execute_query(query, {"name": name})
        return [item['n'] for item in results]
    
    def get_node_by_id(self, node_id: int) -> Optional[Dict]:
        """
        按 ID 获取节点
        
        Args:
            node_id: 节点 ID
            
        Returns:
            节点信息，未找到返回 None
        """
        query = """
        MATCH (n)
        WHERE id(n) = $node_id
        RETURN n
        """
        
        results = self.graph.execute_query(query, {"node_id": node_id})
        return results[0]['n'] if results else None
    
    def get_node_neighbors(self, node_id: int, 
                          depth: int = 1,
                          rel_types: Optional[List[str]] = None) -> Dict:
        """
        获取节点的邻居节点
        
        Args:
            node_id: 节点 ID
            depth: 查询深度
            rel_types: 限制的关系类型
            
        Returns:
            包含节点和邻居的信息
        """
        node = self.get_node_by_id(node_id)
        if not node:
            return {"error": "节点不存在"}
        
        if rel_types:
            rel_pattern = "|".join([f":{rel}" for rel in rel_types])
            query = f"""
            MATCH (n)-[r{rel_pattern}*1..{depth}]-(m)
            WHERE id(n) = $node_id
            RETURN n, r, m
            """
        else:
            query = f"""
            MATCH (n)-[r*1..{depth}]-(m)
            WHERE id(n) = $node_id
            RETURN n, r, m
            """
        
        results = self.graph.execute_query(query, {"node_id": node_id})
        
        neighbors = []
        for item in results:
            if item['m'] and item['m'] != node:
                neighbors.append({
                    "node": item['m'],
                    "relationships": item['r']
                })
        
        return {
            "node": node,
            "neighbors": neighbors,
            "count": len(neighbors)
        }
    
    def query_by_label(self, label: str, 
                       filters: Optional[Dict] = None,
                       limit: int = 100) -> List[Dict]:
        """
        按标签查询节点
        
        Args:
            label: 节点标签
            filters: 过滤条件
            limit: 返回数量限制
            
        Returns:
            节点列表
        """
        where_clauses = []
        params = {"label": label, "limit": limit}
        
        if filters:
            for key, value in filters.items():
                where_clauses.append(f"n.{key} = ${key}")
                params[key] = value
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "true"
        
        query = f"""
        MATCH (n:{label})
        WHERE {where_clause}
        RETURN n
        LIMIT $limit
        """
        
        results = self.graph.execute_query(query, params)
        return [item['n'] for item in results]
    
    def query_relationships(self, start_node: Optional[Dict] = None,
                          end_node: Optional[Dict] = None,
                          rel_type: Optional[str] = None) -> List[Dict]:
        """
        查询关系
        
        Args:
            start_node: 起始节点
            end_node: 结束节点
            rel_type: 关系类型
            
        Returns:
            关系列表
        """
        params = {}
        where_clauses = []
        
        if start_node:
            if 'element_id' in start_node:
                where_clauses.append("id(a) = $start_id")
                params['start_id'] = start_node['element_id']
            elif 'name' in start_node:
                where_clauses.append("a.name = $start_name")
                params['start_name'] = start_node['name']
        
        if end_node:
            if 'element_id' in end_node:
                where_clauses.append("id(b) = $end_id")
                params['end_id'] = end_node['element_id']
            elif 'name' in end_node:
                where_clauses.append("b.name = $end_name")
                params['end_name'] = end_node['name']
        
        rel_pattern = f":{rel_type}" if rel_type else ""
        where_clause = " AND ".join(where_clauses) if where_clauses else "true"
        
        query = f"""
        MATCH (a)-[r{rel_pattern}]->(b)
        WHERE {where_clause}
        RETURN a, r, b
        """
        
        results = self.graph.execute_query(query, params)
        return results
    
    def find_path(self, start_name: str, end_name: str,
                  max_depth: int = 3) -> List[Dict]:
        """
        查找两个节点之间的路径
        
        Args:
            start_name: 起始节点名称
            end_name: 结束节点名称
            max_depth: 最大深度
            
        Returns:
            路径列表
        """
        query = """
        MATCH (start), (end)
        WHERE start.name = $start_name AND end.name = $end_name
        MATCH path = (start)-[*1..$max_depth]-(end)
        RETURN path
        LIMIT 10
        """
        
        results = self.graph.execute_query(query, {
            "start_name": start_name,
            "end_name": end_name,
            "max_depth": max_depth
        })
        
        paths = []
        for item in results:
            if 'path' in item:
                paths.append(item['path'])
        
        return paths
    
    def query_by_entity_type(self, entity_type: str) -> List[Dict]:
        """
        按实体类型查询所有节点
        
        Args:
            entity_type: 实体类型（GPE/GOV_ORG/ORG/PERSON/EVENT/LAW_POLICY）
            
        Returns:
            节点列表
        """
        valid_types = ['GPE', 'GOV_ORG', 'ORG', 'PERSON', 'EVENT', 'LAW_POLICY']
        if entity_type not in valid_types:
            raise ValueError(f"无效的实体类型：{entity_type}")
        
        return self.query_by_label(entity_type)
    
    def get_policy_chain(self, policy_name: str) -> Dict:
        """
        获取政策影响链
        
        Args:
            policy_name: 政策名称
            
        Returns:
            政策影响链信息
        """
        query = """
        MATCH (p:LAW_POLICY {name: $policy_name})
        OPTIONAL MATCH (p)-[:AFFECTS]->(affected)
        OPTIONAL MATCH (issuer)-[:PUBLISHES]->(p)
        RETURN p, affected, issuer
        """
        
        results = self.graph.execute_query(query, {"policy_name": policy_name})
        
        if not results:
            return {"error": "未找到政策"}
        
        affected_nodes = []
        issuers = []
        
        for item in results:
            if item.get('affected'):
                affected_nodes.append(item['affected'])
            if item.get('issuer'):
                issuers.append(item['issuer'])
        
        return {
            "policy": results[0]['p'],
            "affected_by": affected_nodes,
            "issuers": list({str(i): i for i in issuers}.values())
        }
    
    def get_org_connections(self, org_name: str) -> Dict:
        """
        获取组织关联网络
        
        Args:
            org_name: 组织名称
            
        Returns:
            组织关联信息
        """
        query = """
        MATCH (o:ORG {name: $org_name})-[]-(connected)
        RETURN o, connected, relationships(o)
        UNION
        MATCH (o:GOV_ORG {name: $org_name})-[]-(connected)
        RETURN o, connected, relationships(o)
        """
        
        results = self.graph.execute_query(query, {"org_name": org_name})
        
        connections = []
        org_node = None
        
        for item in results:
            if item.get('o'):
                org_node = item['o']
            if item.get('connected'):
                connections.append(item['connected'])
        
        return {
            "organization": org_node,
            "connections": connections,
            "count": len(connections)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取图谱统计信息
        
        Returns:
            统计信息
        """
        stats_query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
        """
        
        rel_query = """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
        """
        
        node_stats = self.graph.execute_query(stats_query)
        rel_stats = self.graph.execute_query(rel_query)
        
        total_nodes = sum(item['count'] for item in node_stats)
        total_rels = sum(item['count'] for item in rel_stats)
        
        return {
            "total_nodes": total_nodes,
            "total_relationships": total_rels,
            "nodes_by_type": {item['label']: item['count'] for item in node_stats},
            "relationships_by_type": {item['type']: item['count'] for item in rel_stats},
            "timestamp": datetime.now().isoformat()
        }
    
    def export_subgraph(self, center_name: str, 
                       depth: int = 2) -> Dict[str, Any]:
        """
        导出子图
        
        Args:
            center_name: 中心节点名称
            depth: 深度
            
        Returns:
            子图数据（nodes 和 relationships）
        """
        query = """
        MATCH (center)
        WHERE center.name = $center_name
        MATCH (center)-[*0..$depth]-(neighbor)
        RETURN center, neighbor, relationships(center, neighbor)
        """
        
        results = self.graph.execute_query(query, {
            "center_name": center_name,
            "depth": depth
        })
        
        nodes = {}
        relationships = []
        
        for item in results:
            if item.get('center'):
                nodes[str(item['center']['element_id'])] = item['center']
            if item.get('neighbor'):
                nodes[str(item['neighbor']['element_id'])] = item['neighbor']
        
        return {
            "nodes": list(nodes.values()),
            "relationships": relationships,
            "center": center_name,
            "depth": depth
        }
    
    def close(self):
        """关闭连接"""
        if self.graph:
            self.graph.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 便捷函数
def get_query_interface() -> KnowledgeGraphQuery:
    """获取查询接口实例"""
    return KnowledgeGraphQuery()


if __name__ == "__main__":
    # 测试查询
    with get_query_interface() as query:
        print("统计:", query.get_statistics())
        
        # 搜索测试
        results = query.search_by_name("中国")
        print("搜索结果:", results)
