"""
Knowledge Graph Builder Module
知识图谱构建器 - 用于创建和填充知识图谱
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from graph import Neo4jGraph, get_graph_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """知识图谱构建器"""
    
    def __init__(self, graph: Optional[Neo4jGraph] = None):
        """
        初始化构建器
        
        Args:
            graph: Neo4jGraph 实例，如果不提供则自动创建
        """
        self.graph = graph or get_graph_connection()
        self._created_nodes = []
        self._created_relationships = []
    
    def create_gpe(self, name: str, code: Optional[str] = None, 
                   full_name: Optional[str] = None, **kwargs) -> Dict:
        """
        创建国家/地区节点
        
        Args:
            name: 名称（如：中国）
            code: 代码（如：CN）
            full_name: 全称（如：中华人民共和国）
            **kwargs: 其他属性
            
        Returns:
            创建的节点信息
        """
        properties = {
            "name": name,
            "code": code,
            "full_name": full_name or name,
            "created_at": datetime.now().isoformat(),
            **kwargs
        }
        
        node = self.graph.create_node('GPE', properties)
        self._created_nodes.append(node)
        logger.info(f"创建 GPE: {name}")
        return node
    
    def create_gov_org(self, name: str, level: str = "national",
                       parent_org: Optional[str] = None, **kwargs) -> Dict:
        """
        创建政府机构节点
        
        Args:
            name: 机构名称
            level: 级别（national/provincial/municipal）
            parent_org: 上级机构名称
            **kwargs: 其他属性
            
        Returns:
            创建的节点信息
        """
        properties = {
            "name": name,
            "level": level,
            "created_at": datetime.now().isoformat(),
            **kwargs
        }
        
        node = self.graph.create_node('GOV_ORG', properties)
        self._created_nodes.append(node)
        
        # 如果有上级机构，创建隶属关系
        if parent_org:
            parent_node = self.graph.find_node('GOV_ORG', {"name": parent_org})
            if parent_node:
                self.create_relationship(
                    node['element_id'], 
                    parent_node['element_id'],
                    'BELONGS_TO'
                )
        
        logger.info(f"创建 GOV_ORG: {name}")
        return node
    
    def create_org(self, name: str, org_type: str = "company",
                   industry: Optional[str] = None, **kwargs) -> Dict:
        """
        创建公司/组织节点
        
        Args:
            name: 组织名称
            org_type: 类型（company/ngo/association 等）
            industry: 所属行业
            **kwargs: 其他属性
            
        Returns:
            创建的节点信息
        """
        properties = {
            "name": name,
            "org_type": org_type,
            "industry": industry,
            "created_at": datetime.now().isoformat(),
            **kwargs
        }
        
        node = self.graph.create_node('ORG', properties)
        self._created_nodes.append(node)
        logger.info(f"创建 ORG: {name}")
        return node
    
    def create_person(self, name: str, title: Optional[str] = None,
                      organization: Optional[str] = None, **kwargs) -> Dict:
        """
        创建人物节点
        
        Args:
            name: 姓名
            title: 职务/头衔
            organization: 所属组织
            **kwargs: 其他属性
            
        Returns:
            创建的节点信息
        """
        properties = {
            "name": name,
            "title": title,
            "created_at": datetime.now().isoformat(),
            **kwargs
        }
        
        node = self.graph.create_node('PERSON', properties)
        self._created_nodes.append(node)
        
        # 如果有所属组织，创建关系
        if organization:
            org_node = self.graph.find_node('ORG', {"name": organization})
            if not org_node:
                org_node = self.graph.find_node('GOV_ORG', {"name": organization})
            
            if org_node:
                self.create_relationship(
                    node['element_id'],
                    org_node['element_id'],
                    'BELONGS_TO'
                )
        
        logger.info(f"创建 PERSON: {name}")
        return node
    
    def create_event(self, name: str, event_type: str,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     location: Optional[str] = None, **kwargs) -> Dict:
        """
        创建事件节点
        
        Args:
            name: 事件名称
            event_type: 事件类型
            start_date: 开始日期
            end_date: 结束日期
            location: 地点
            **kwargs: 其他属性
            
        Returns:
            创建的节点信息
        """
        properties = {
            "name": name,
            "event_type": event_type,
            "start_date": start_date,
            "end_date": end_date,
            "location": location,
            "created_at": datetime.now().isoformat(),
            **kwargs
        }
        
        node = self.graph.create_node('EVENT', properties)
        self._created_nodes.append(node)
        
        # 如果有地点，创建位置关系
        if location:
            location_node = self.graph.find_node('GPE', {"name": location})
            if location_node:
                self.create_relationship(
                    node['element_id'],
                    location_node['element_id'],
                    'LOCATED_IN'
                )
        
        logger.info(f"创建 EVENT: {name}")
        return node
    
    def create_law_policy(self, name: str, law_type: str = "policy",
                          issue_date: Optional[str] = None,
                          issuer: Optional[str] = None, **kwargs) -> Dict:
        """
        创建政策/法规节点
        
        Args:
            name: 政策/法规名称
            law_type: 类型（law/regulation/policy/standard）
            issue_date: 发布日期
            issuer: 发布机构
            **kwargs: 其他属性
            
        Returns:
            创建的节点信息
        """
        properties = {
            "name": name,
            "law_type": law_type,
            "issue_date": issue_date,
            "created_at": datetime.now().isoformat(),
            **kwargs
        }
        
        node = self.graph.create_node('LAW_POLICY', properties)
        self._created_nodes.append(node)
        
        # 如果有发布机构，创建发布关系
        if issuer:
            issuer_node = self.graph.find_node('GOV_ORG', {"name": issuer})
            if not issuer_node:
                issuer_node = self.graph.find_node('ORG', {"name": issuer})
            
            if issuer_node:
                self.create_relationship(
                    issuer_node['element_id'],
                    node['element_id'],
                    'PUBLISHES'
                )
        
        logger.info(f"创建 LAW_POLICY: {name}")
        return node
    
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
        rel = self.graph.create_relationship(
            start_node_id, end_node_id, rel_type, properties
        )
        self._created_relationships.append(rel)
        return rel
    
    def link_gpe_location(self, org_name: str, gpe_name: str):
        """
        链接组织/机构到所在地
        
        Args:
            org_name: 组织/机构名称
            gpe_name: 国家/地区名称
        """
        org_node = self.graph.find_node('ORG', {"name": org_name})
        if not org_node:
            org_node = self.graph.find_node('GOV_ORG', {"name": org_name})
        
        gpe_node = self.graph.find_node('GPE', {"name": gpe_name})
        
        if org_node and gpe_node:
            self.create_relationship(
                org_node['element_id'],
                gpe_node['element_id'],
                'LOCATED_IN'
            )
            logger.info(f"链接位置：{org_name} -> {gpe_name}")
    
    def link_policy_impact(self, policy_name: str, target_name: str,
                          target_type: str = 'ORG'):
        """
        链接政策影响关系
        
        Args:
            policy_name: 政策名称
            target_name: 影响目标名称
            target_type: 目标类型
        """
        policy_node = self.graph.find_node('LAW_POLICY', {"name": policy_name})
        target_node = self.graph.find_node(target_type, {"name": target_name})
        
        if policy_node and target_node:
            self.create_relationship(
                policy_node['element_id'],
                target_node['element_id'],
                'AFFECTS'
            )
            logger.info(f"链接影响：{policy_name} -> {target_name}")
    
    def link_cooperation(self, org1_name: str, org2_name: str):
        """
        链接合作关系
        
        Args:
            org1_name: 组织 1 名称
            org2_name: 组织 2 名称
        """
        org1_node = self.graph.find_node('ORG', {"name": org1_name})
        if not org1_node:
            org1_node = self.graph.find_node('GOV_ORG', {"name": org1_name})
        
        org2_node = self.graph.find_node('ORG', {"name": org2_name})
        if not org2_node:
            org2_node = self.graph.find_node('GOV_ORG', {"name": org2_name})
        
        if org1_node and org2_node:
            self.create_relationship(
                org1_node['element_id'],
                org2_node['element_id'],
                'COOPERATES_WITH'
            )
            logger.info(f"链接合作：{org1_name} <-> {org2_name}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取构建统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "nodes_created": len(self._created_nodes),
            "relationships_created": len(self._created_relationships),
            "timestamp": datetime.now().isoformat()
        }
    
    def build_sample_graph(self):
        """构建示例图谱用于测试"""
        logger.info("开始构建示例图谱...")
        
        # 创建国家
        china = self.create_gpe("中国", "CN", "中华人民共和国")
        usa = self.create_gpe("美国", "US", "美利坚合众国")
        
        # 创建政府机构
        ndrc = self.create_gov_org("国家发展和改革委员会", "national")
        miit = self.create_gov_org("工业和信息化部", "national")
        
        # 创建公司
        tencent = self.create_org("腾讯", "company", "互联网")
        alibaba = self.create_org("阿里巴巴", "company", "互联网")
        
        # 创建人物
        person1 = self.create_person("张三", "工程师", "腾讯")
        
        # 创建政策
        policy1 = self.create_law_policy(
            "数据安全法",
            "law",
            "2021-09-01",
            "国家发展和改革委员会"
        )
        
        # 创建事件
        event1 = self.create_event(
            "数字经济峰会",
            "conference",
            "2024-01-15",
            "2024-01-17",
            "北京"
        )
        
        # 创建关系
        self.link_gpe_location("腾讯", "中国")
        self.link_gpe_location("阿里巴巴", "中国")
        self.link_policy_impact("数据安全法", "腾讯")
        self.link_cooperation("腾讯", "阿里巴巴")
        
        stats = self.get_statistics()
        logger.info(f"示例图谱构建完成：{stats}")
        
        return stats
    
    def close(self):
        """关闭连接"""
        if self.graph:
            self.graph.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 便捷函数
def get_builder() -> KnowledgeGraphBuilder:
    """获取图谱构建器实例"""
    return KnowledgeGraphBuilder()


if __name__ == "__main__":
    # 测试构建器
    with get_builder() as builder:
        builder.build_sample_graph()
        print("统计:", builder.get_statistics())
