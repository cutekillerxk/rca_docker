#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM调用封装
替代LangChain，直接调用vLLM/OpenAI API
支持Role Token注入
"""

import os
import json
import requests
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

# 导入配置
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cl_agent.config import (
    VLLM_BASE_URL,
    VLLM_MODEL_PATH,
    THIRD_PARTY_API_BASE_URL,
    THIRD_PARTY_API_KEY
)


class LLMClient:
    """
    LLM客户端封装
    支持vLLM和第三方API（OpenAI兼容）
    """
    
    def __init__(
        self,
        model_name: str = "qwen-8b",
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        max_tokens: Optional[int] = None
    ):
        """
        初始化LLM客户端
        
        Args:
            model_name: 模型名称，可选值：qwen-8b, gpt-4o, deepseek-r1
            base_url: API基础URL（可选，默认从配置读取）
            api_key: API密钥（可选，默认从配置读取）
            timeout: 超时时间（秒，可选，默认值根据模型类型：qwen-8b/deepseek-r1=120, gpt-4o=60）
            max_tokens: 最大token数（可选，默认4096）
        """
        self.model_name = model_name
        
        # 模型配置字典
        # 根据 cl_agent/agent.py 的实现，使用相同的默认配置值
        # 如果传入了 timeout 或 max_tokens 参数，会使用传入的值；否则使用与 cl_agent 一致的默认值
        model_configs = {
            "qwen-8b": {
                "base_url": base_url or VLLM_BASE_URL,
                "api_key": api_key or "not-needed",
                "model": VLLM_MODEL_PATH,  # 直接使用完整路径，与 cl_agent/agent.py 保持一致
                "timeout": timeout if timeout is not None else 120,  # 默认值与 cl_agent/agent.py 一致
                "max_tokens": max_tokens if max_tokens is not None else 4096,  # 默认值与 cl_agent/agent.py 一致
            },
            "gpt-4o": {
                "base_url": base_url or THIRD_PARTY_API_BASE_URL,
                "api_key": api_key or THIRD_PARTY_API_KEY,
                "model": "gpt-4o",
                "timeout": timeout if timeout is not None else 60,  # 默认值与 cl_agent/agent.py 一致
                "max_tokens": max_tokens if max_tokens is not None else 4096,  # 默认值与 cl_agent/agent.py 一致
            },
            "deepseek-r1": {
                "base_url": base_url or THIRD_PARTY_API_BASE_URL,
                "api_key": api_key or THIRD_PARTY_API_KEY,
                "model": "DeepSeek-V3.2",
                "timeout": timeout if timeout is not None else 120,  # 默认值与 cl_agent/agent.py 一致
                "max_tokens": max_tokens if max_tokens is not None else 4096,  # 默认值与 cl_agent/agent.py 一致
            }
        }
        
        # 获取模型配置
        if model_name not in model_configs:
            raise ValueError(f"不支持的模型名称: {model_name}")
        
        config = model_configs[model_name]
        
        # 检查第三方API配置
        if model_name in ["gpt-4o", "deepseek-r1"]:
            if not config["base_url"] or not config["api_key"]:
                raise ValueError(
                    f"模型 {model_name} 需要配置 API_BASE_URL 和 API_KEY 环境变量" 
                )
        
        self.base_url = config["base_url"]
        self.api_key = config["api_key"]
        self.model = config["model"]
        self.timeout = config["timeout"]
        self.max_tokens = config["max_tokens"]
        
        print(f"[LLMClient] 初始化完成 - 模型: {model_name}, base_url: {self.base_url}")
        print(f"[LLMClient] API调用时将使用的模型标识符: {self.model}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0,
        role_token: Optional[str] = None
    ) -> str:
        """
        生成文本
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            temperature: 温度参数
            role_token: Role Token（可选，如 "<ROLE=classifier>"）
        
        Returns:
            生成的文本
        """
        # 构建完整prompt
        full_prompt = ""
        
        # 添加Role Token（如果提供）
        if role_token:
            full_prompt += f"{role_token}\n"
        
        # 添加系统提示
        if system_prompt:
            full_prompt += f"{system_prompt}\n\n"
        
        # 添加用户提示
        full_prompt += prompt
        
        # 构建消息列表
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # 调用API
        return self._call_api(messages, temperature)
    
    def generate_with_role(
        self,
        role: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0
    ) -> str:
        """
        带Role Token的生成
        
        Args:
            role: Role名称，如 "classifier", "hdfs_expert"
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            temperature: 温度参数
        
        Returns:
            生成的文本
        """
        role_token = f"<ROLE={role}>"
        return self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            role_token=role_token
        )
    
    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        role_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成JSON格式输出
        
        Args:
            prompt: 用户提示（应包含JSON格式要求）
            system_prompt: 系统提示（可选）
            role_token: Role Token（可选）
        
        Returns:
            解析后的JSON字典
        """
        # 在prompt中添加JSON格式要求
        json_prompt = f"{prompt}\n\n请以JSON格式输出，确保输出是有效的JSON。"
        
        response = self.generate(
            prompt=json_prompt,
            system_prompt=system_prompt,
            temperature=0,  # JSON生成使用temperature=0确保稳定性
            role_token=role_token
        )
        
        # 尝试解析JSON
        try:
            # 移除可能的markdown代码块标记
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            elif response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"[WARNING] JSON解析失败: {e}")
            print(f"[WARNING] 原始响应: {response[:200]}")
            # 尝试提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            raise ValueError(f"无法解析JSON响应: {response[:200]}")
    
    def _call_api(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0
    ) -> str:
        """
        调用LLM API
        
        Args:
            messages: 消息列表
            temperature: 温度参数
        
        Returns:
            生成的文本
        """
        # 构建API请求
        # 根据 cl_agent/agent.py 的实现，VLLM_BASE_URL 已经包含 /v1
        # 直接拼接 /chat/completions 即可
        base_url_clean = self.base_url.rstrip('/')
        url = f"{base_url_clean}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
        }
        
        # 添加API密钥（如果需要）
        if self.api_key and self.api_key != "not-needed":
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.max_tokens,
        }
        
        # 添加调试信息
        print(f"[DEBUG] API请求URL: {url}")
        print(f"[DEBUG] API请求模型: {self.model}")
        print(f"[DEBUG] API请求payload: {json.dumps(payload, ensure_ascii=False, indent=2)[:500]}...")
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            result = response.json()
            
            # 提取生成的文本
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                # 清理响应（移除推理标记等）
                content = self._clean_response(content)
                return content
            else:
                raise ValueError(f"API响应格式错误: {result}")
        
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"API调用失败: {str(e)}")
        except KeyError as e:
            raise ValueError(f"API响应格式错误，缺少字段: {e}")
    
    def _clean_response(self, response: str) -> str:
        """
        清理LLM响应（移除推理标记等）
        
        Args:
            response: 原始响应文本
        
        Returns:
            清理后的文本
        """
        import re
        # 移除常见的推理标记
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
        response = re.sub(r'<reasoning>.*?</reasoning>', '', response, flags=re.DOTALL)
        # 清理多余的空白字符
        response = re.sub(r'\n{3,}', '\n\n', response)  # 多个换行符合并为两个
        response = response.strip()
        return response
