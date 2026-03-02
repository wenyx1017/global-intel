"""
Neo4j Graph Operations Module
提供 Neo4j 数据库连接和基础操作
"""

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
from typing import Optional, List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jGraph:
    """Neo4j 图数据库操作类"""
    
    # 实体标签
    LABELS = {
        'GPE': 'GPE',  # 国家/地区
        'GOV_ORG': 'GOV_ORG',  # 政府机构
        'ORG': 'ORG',  # 公司/组织
        'PERSON': 'PERSON',  # 人物
        'EVENT': 'EVENT',  # 事件
        'LAW_POLICY': 'LAW_POLICY',  # 政策/法规
    }
    
    # 关系类型
    RELATIONS = {
        'BELONGS_TO': 'BELONGS_TO',  # 隶属于
        'LOCATED_IN': 'LOCATED_IN',  # 位于
        'PUBLISHES': 'PUBLISHES',  # 发布
        'IMPLEMENTS': 'IMPLEMENTS',  # 实施
        'AFFECTS': 'AFFECTS',  # 影响
        'AFFECTED_BY': 'AFFECTED_BY',  # 被影响
        'COOPERATES_WITH': 'COOPERATES_WITH',  # 合作
        'CONFLICTS_WITH': 'CONFLICTS_WITH',  # 对抗
    }
    
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 user: str = "neo4j", 
                 password: str = "knowledge_graph_2024"):
        """
        初始化 Neo4j 连接
        
        Args:
            uri: Neo4j Bolt URI
            user: 用户名
            password: 密码
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self._connect()
    
    def _connect(self):
        """建立数据库连接"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # 验证连接
            self.driver.verify_connectivity()
            logger.info(f"成功连接到 Neo4j: {self.uri}")
        except ServiceUnavailable as e:
            logger.error(f"无法连接到 Neo4j: {e}")
            raise
        except AuthError as e:
            logger.error(f"认证失败: {e}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j 连接已关闭")
    
    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """
        执行 Cypher 查询
        
        Args:
            query: Cypher 查询语句
            parameters: 查询参数
            
        Returns:
            查询结果列表
        """
        if not self.driver:
            raise RuntimeError("数据库未连接")
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            raise
    
    def create_node(self, label: str, properties: Dict[str, Any]) -> Dict:
        """
        创建节点
        
        Args:
            label: 节点标签
            properties: 节点属性
            
        Returns:
            创建的节点信息
        """
        if label not in self.LABELS.values():
            raise ValueError(f"无效的节点标签：{label}")
        
        query = f"""
        CREATE (n:{label} $properties)
        RETURN n
        """
        
        result = self.execute_query(query, {"properties": properties})
        logger.info(f"创建节点：{label}, {properties.get('name', 'N/A')}")
        return result[0]['n'] if result else {}
    
    def create_relationship(self, start_node_id: str, end_node_id: str, 
                          rel_type: str, properties: Optional[Dict] = None) -> Dict:
        """
        创建关系
        
        Args:
            start_node_id: 起始节点 ID
            end_node_id: 结束节点 ID
            rel_type: 关系类型
            properties: 关系属性
            
        Returns:
            创建的关系信息
        """
        if rel_type not in self.RELATIONS.values():
            raise ValueError(f"无效的关系类型：{rel_type}")
        
        query = f"""
        MATCH (a), (b)
        WHERE id(a) = $start_id AND id(b) = $end_id
        CREATE (a)-[r:{rel_type} $properties]->(b)
        RETURN r
        """
        
        result = self.execute_query(query, {
            "start_id": start_node_id,
            "end_id": end_node_id,
            "properties": properties or {}
        })
        
        logger.info(f"创建关系：{rel_type} ({start_node_id} -> {end_node_id})")
        return result[0]['r'] if result else {}
    
    def find_node(self, label: str, properties: Dict[str, Any]) -> Optional[Dict]:
        """
        查找节点
        
        Args:
            label: 节点标签
            properties: 匹配属性
            
        Returns:
            匹配的节点，未找到返回 None
        """
        where_clauses = []
        for key in properties.keys():
            where_clauses.append(f"n.${key} = ${key}")
        
        where_clause = " AND ".join(where_clauses)
        
        query = f"""
        MATCH (n:{label})
        WHERE {where_clause}
        RETURN n
        """
        
        result = self.execute_query(query, properties)
        return result[0]['n'] if result else None
    
    def delete_node(self, node_id: int, detach: bool = True):
        """
        删除节点
        
        Args:
            node_id: 节点 ID
            detach: 是否先删除相关关系
        """
        if detach:
            query = """
            MATCH (n)
            WHERE id(n) = $node_id
            DETACH DELETE n
            """
        else:
            query = """
            MATCH (n)
            WHERE id(n) = $node_id
            DELETE n
            """
        
        self.execute_query(query, {"node_id": node_id})
        logger.info(f"删除节点：{node_id}")
    
    def get_schema(self) -> Dict[str, Any]:
        """
        获取数据库 schema 信息
        
        Returns:
            schema 信息字典
        """
        labels_query = "CALL db.labels()"
        rels_query = "CALL db.relationshipTypes()"
        
        labels = self.execute_query(labels_query)
        relationships = self.execute_query(rels_query)
        
        return {
            "labels": [item['label'] for item in labels],
            "relationships": [item['relationshipType'] for item in relationships]
        }
    
    def clear_database(self):
        """清空数据库（危险操作）"""
        query = "MATCH (n) DETACH DELETE n"
        self.execute_query(query)
        logger.warning("数据库已清空")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 便捷函数
def get_graph_connection() -> Neo4jGraph:
    """获取图数据库连接实例"""
    return Neo4jGraph()


if __name__ == "__main__":
    # 测试连接
    with get_graph_connection() as graph:
        print("Schema:", graph.get_schema())
