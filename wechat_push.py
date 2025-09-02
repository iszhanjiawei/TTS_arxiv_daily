#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信推送模块
支持企业微信机器人和Server酱推送
"""

import requests
import json
import logging
from typing import Dict, List, Optional

class WeChatPusher:
    """微信推送类"""
    
    def __init__(self, config: Dict):
        """
        初始化微信推送器
        
        Args:
            config: 配置字典，包含推送相关配置
        """
        self.config = config
        self.enabled = config.get('wechat_push', {}).get('enabled', False)
        self.webhook_url = config.get('wechat_push', {}).get('webhook_url', '')
        self.serverchan_key = config.get('wechat_push', {}).get('serverchan_key', '')
        self.push_method = config.get('wechat_push', {}).get('method', 'webhook')  # webhook 或 serverchan
        
    def is_enabled(self) -> bool:
        """检查是否启用微信推送"""
        return self.enabled and (self.webhook_url or self.serverchan_key)
    
    def format_papers_message(self, papers_data: Dict, date_str: str) -> str:
        """
        格式化论文数据为微信消息
        
        Args:
            papers_data: 论文数据字典
            date_str: 日期字符串
            
        Returns:
            格式化后的消息字符串
        """
        if not papers_data:
            return f"📚 TTS论文日报 {date_str}\n\n今日暂无新论文更新。"
        
        message_parts = [f"📚 TTS论文日报 {date_str}"]
        
        total_papers = 0
        for topic, papers in papers_data.items():
            if papers:
                total_papers += len(papers)
                message_parts.append(f"\n🔍 {topic} ({len(papers)}篇)")
                
                # 显示所有当日论文
                for paper_id, paper_info in papers.items():
                    # 解析论文信息
                    # 格式: |**2024-06-07**|**Title**|Author et.al.|[2406.04843](http://arxiv.org/abs/2406.04843)|null|
                    parts = paper_info.split('|')
                    if len(parts) >= 5:
                        date = parts[1].replace('**', '').strip()
                        title = parts[2].replace('**', '').strip()
                        author = parts[3].strip()
                        url = f"https://arxiv.org/abs/{paper_id}"
                        
                        # 限制标题长度
                        if len(title) > 50:
                            title = title[:47] + "..."
                        
                        message_parts.append(f"• {title}")
                        message_parts.append(f"  👤 {author}")
                        message_parts.append(f"  🔗 {url}")
        
        if total_papers > 0:
            message_parts.append(f"\n📊 今日共更新 {total_papers} 篇论文")
            message_parts.append("\n🔗 完整列表: https://github.com/iszhanjiawei/TTS_arxiv_daily")
        
        return "\n".join(message_parts)
    
    def send_webhook_message(self, message: str) -> bool:
        """
        通过企业微信机器人发送消息
        
        Args:
            message: 要发送的消息内容
            
        Returns:
            发送是否成功
        """
        if not self.webhook_url:
            logging.error("企业微信Webhook URL未配置")
            return False
        
        data = {
            "msgtype": "text",
            "text": {
                "content": message
            }
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    logging.info("企业微信消息发送成功")
                    return True
                else:
                    logging.error(f"企业微信消息发送失败: {result.get('errmsg')}")
                    return False
            else:
                logging.error(f"企业微信消息发送失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            logging.error(f"发送企业微信消息时出错: {str(e)}")
            return False
    
    def send_serverchan_message(self, message: str, title: str = "TTS论文日报") -> bool:
        """
        通过Server酱发送消息到微信
        
        Args:
            message: 要发送的消息内容
            title: 消息标题
            
        Returns:
            发送是否成功
        """
        if not self.serverchan_key:
            logging.error("Server酱密钥未配置")
            return False
        
        url = f"https://sctapi.ftqq.com/{self.serverchan_key}.send"
        
        data = {
            "title": title,
            "desp": message
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    logging.info("Server酱消息发送成功")
                    return True
                else:
                    logging.error(f"Server酱消息发送失败: {result.get('message')}")
                    return False
            else:
                logging.error(f"Server酱消息发送失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            logging.error(f"发送Server酱消息时出错: {str(e)}")
            return False
    
    def push_daily_papers(self, papers_data: Dict, date_str: str) -> bool:
        """
        推送每日论文更新
        
        Args:
            papers_data: 论文数据字典
            date_str: 日期字符串
            
        Returns:
            推送是否成功
        """
        if not self.is_enabled():
            logging.info("微信推送未启用或配置不完整")
            return False
        
        # 格式化消息
        message = self.format_papers_message(papers_data, date_str)
        
        # 根据配置选择推送方式
        if self.push_method == 'webhook' and self.webhook_url:
            return self.send_webhook_message(message)
        elif self.push_method == 'serverchan' and self.serverchan_key:
            return self.send_serverchan_message(message)
        else:
            logging.error(f"不支持的推送方式: {self.push_method}")
            return False
    
    def test_connection(self) -> bool:
        """
        测试连接
        
        Returns:
            连接测试是否成功
        """
        if not self.is_enabled():
            logging.error("微信推送未启用或配置不完整")
            return False
        
        test_message = "🔧 TTS论文推送测试消息\n\n如果您收到此消息，说明微信推送配置成功！"
        
        if self.push_method == 'webhook':
            return self.send_webhook_message(test_message)
        elif self.push_method == 'serverchan':
            return self.send_serverchan_message(test_message, "TTS论文推送测试")
        else:
            return False


def create_wechat_pusher(config: Dict) -> WeChatPusher:
    """
    创建微信推送器实例
    
    Args:
        config: 配置字典
        
    Returns:
        WeChatPusher实例
    """
    return WeChatPusher(config)


if __name__ == "__main__":
    # 测试代码
    import yaml
    
    # 加载配置
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    
    # 创建推送器
    pusher = create_wechat_pusher(config)
    
    # 测试连接
    if pusher.test_connection():
        print("微信推送测试成功！")
    else:
        print("微信推送测试失败，请检查配置。")