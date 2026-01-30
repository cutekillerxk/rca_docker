#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多智能体框架 - Gradio Web 界面版本
基于多智能体框架（分类+专家+讨论）实现故障诊断

使用方法：
    python mutli_agent/gradio_demo.py
    
在浏览器中打开显示的 URL（通常是 http://127.0.0.1:7860）
"""

import gradio as gr
import sys
import os
import signal
import json
import re
from datetime import datetime

# 添加父目录到路径，以便导入现有模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入多智能体框架
from mutli_agent import FaultOrchestrator, LLMClient
from cl_agent.monitor_collector import collect_all_metrics, format_metrics_for_display
from cl_agent.agent import export_to_word, export_to_pdf

# 全局 Orchestrator 实例和当前模型
orchestrator = None
current_model = "qwen-8b"  # 当前使用的模型
# 存储最后一次的诊断回复（用于文档导出）
last_diagnosis_response = ""
# 全局 Gradio demo 实例（用于优雅关闭）
demo_instance = None
# 关闭标志，防止重复关闭
_shutting_down = False

# 模型名称映射（前端显示名称 -> 内部模型名称）
MODEL_NAME_MAP = {
    "Qwen-8B (vLLM)": "qwen-8b",
    "GPT-4o (OpenAI)": "gpt-4o",
    "DeepSeek-R1 (DeepSeek)": "deepseek-r1"
}


def init_orchestrator(model_name: str = "qwen-8b"):
    """
    初始化多智能体协调器（支持模型切换） 
    
    Args:
        model_name: 模型名称，可选值：qwen-8b, gpt-4o, deepseek-r1
    """
    global orchestrator, current_model
    
    model_display_name = {v: k for k, v in MODEL_NAME_MAP.items()}.get(model_name, model_name)
    
    # 如果模型改变或Orchestrator未初始化，重新创建
    if orchestrator is None:
        print(f"[INFO] Orchestrator未初始化，正在创建（模型: {model_display_name}）...")
        try:
            llm_client = LLMClient(model_name=model_name)
            orchestrator = FaultOrchestrator(llm_client, model_name=model_name)
            current_model = model_name
            print(f"[INFO] ✅ 多智能体协调器初始化完成（模型: {model_display_name}）")
        except Exception as e:
            error_msg = f"多智能体协调器初始化失败: {str(e)}"
            print(f"[ERROR] {error_msg}")
            raise RuntimeError(error_msg)
    elif current_model != model_name:
        print(f"[INFO] 检测到模型切换请求:")
        print(f"[INFO]   当前模型: {current_model} ({MODEL_NAME_MAP.get(current_model, current_model)})")
        print(f"[INFO]   目标模型: {model_name} ({model_display_name})")
        print(f"[INFO] 正在重新创建Orchestrator...")
        try:
            llm_client = LLMClient(model_name=model_name)
            orchestrator = FaultOrchestrator(llm_client, model_name=model_name)
            old_model = current_model
            current_model = model_name
            print(f"[INFO] ✅ 模型切换成功:")
            print(f"[INFO]   从: {old_model} ({MODEL_NAME_MAP.get(old_model, old_model)})")
            print(f"[INFO]   到: {current_model} ({model_display_name})")
        except Exception as e:
            error_msg = f"模型切换失败: {str(e)}"
            print(f"[ERROR] {error_msg}")
            raise RuntimeError(error_msg)
    else:
        print(f"[DEBUG] 使用现有Orchestrator（模型: {model_display_name}）")
    
    return orchestrator


def update_monitoring_display():
    """更新监控数据显示"""
    try:
        metrics_data = collect_all_metrics()
        html_content = format_metrics_for_display(metrics_data)
        return html_content
    except Exception as e:
        error_html = f"<div style='color: red; padding: 20px;'>❌ 获取监控数据失败: {str(e)}</div>"
        return error_html


def create_gradio_interface():
    """创建 Gradio 界面"""
    
    # 自定义 CSS 样式
    custom_css = """
    .gradio-container {
        font-family: 'Microsoft YaHei', 'PingFang SC', Arial, sans-serif;
    }
    .chat-message {
        padding: 10px;
    }
    """
    
    # 使用 Blocks 创建更灵活的布局
    with gr.Blocks(title="Hadoop 集群监控 Agent (多智能体框架)", theme=gr.themes.Soft(), css=custom_css) as demo:
        # 使用两列布局：左侧（标题+监控），右侧（聊天）
        with gr.Row():
            # 左侧列：标题+功能说明 + 监控数据
            with gr.Column(scale=1, min_width=300):
                # 标题和功能说明
                gr.Markdown("""
                #  Hadoop 集群监控智能助手
                
                **多智能体框架**：
                - 📋 **分类Agent**：自动识别故障类型
                - 🔍 **专家Agent**：多专家并行诊断（HDFS/YARN/MapReduce/Network）
                - 💬 **讨论Agent**：综合专家意见，生成最终诊断
                - 📊 **实时监控**：显示集群关键指标
                - 🤖 **多模型支持**：支持切换 Qwen-8B、GPT-4o、DeepSeek-R1
                
                **诊断流程**：
                1. 收集全局上下文（日志+监控）
                2. 分类Agent识别故障类型
                3. 选择相关专家并行诊断
                4. Discussion Agent综合结果
                """)
                
                gr.Markdown("### 📊 集群监控指标")
                monitoring_html = gr.HTML(
                    value="<div style='padding: 20px; text-align: center;'>正在加载监控数据...</div>",
                    label="监控数据",
                    elem_id="monitoring-display"
                )
                
                # 刷新按钮
                refresh_btn = gr.Button("🔄 手动刷新", variant="primary", size="sm")
                
                def refresh_monitoring():
                    """手动刷新监控数据""" 
                    return update_monitoring_display()
                
                refresh_btn.click(
                    fn=refresh_monitoring,
                    inputs=None,
                    outputs=monitoring_html
                )
                
                # 导出按钮
                with gr.Row():
                    export_word_btn = gr.Button("📄 导出Word", variant="secondary", size="sm", scale=1)
                    export_pdf_btn = gr.Button("📄 导出PDF", variant="secondary", size="sm", scale=1)
                
                # 导出状态
                export_status = gr.Textbox(
                    label="导出状态",
                    visible=True,
                    interactive=False,
                    lines=2
                )
                
                # 文件下载组件
                export_file = gr.File(
                    label="下载文件",
                    visible=True,
                    interactive=False,
                    height=50
                )
            
            # 右侧列：聊天对话
            with gr.Column(scale=2, min_width=400):
                gr.Markdown("### 💬 多智能体诊断（分类→专家→讨论）")
                
                # 模型选择下拉框
                model_selector = gr.Dropdown(
                    choices=list(MODEL_NAME_MAP.keys()),
                    value="Qwen-8B (vLLM)",
                    label="选择大模型",
                    info="切换不同的大模型进行对话",
                    interactive=True
                )
                
                chatbot = gr.Chatbot(
                    label="对话历史",
                    height=500,
                    show_copy_button=True
                )
                msg = gr.Textbox(
                    label="输入消息",
                    placeholder="输入您的问题，例如：查看集群状态、分析是否有故障、检查DataNode状态",
                    lines=2
                )
                
                with gr.Row():
                    submit_btn = gr.Button("📤 发送", variant="primary")
                    clear_btn = gr.Button("🗑️ 清空", variant="secondary")
                
                # 示例问题
                gr.Examples(
                    examples=[
                        "查看集群状态，分析是否有故障",
                        "检查DataNode是否正常",
                        "分析YARN任务失败的原因",
                        "诊断MapReduce任务内存不足问题",
                    ],
                    inputs=msg
                )
        
        # 模型切换功能
        def switch_model(selected_model, chat_history):
            """切换模型并清空对话历史"""
            global orchestrator, current_model
            
            # 检查模型名称是否在映射中
            if selected_model not in MODEL_NAME_MAP:
                error_msg = f"❌ 未知的模型选择: {selected_model}，请选择有效的模型"
                print(f"[ERROR] {error_msg}")
                if chat_history:
                    chat_history.append(["", error_msg])
                else:
                    chat_history = [["", error_msg]]
                return chat_history
            
            model_name = MODEL_NAME_MAP[selected_model]
            
            if current_model != model_name:
                try:
                    orchestrator = None
                    init_orchestrator(model_name)
                    return []
                except Exception as e:
                    error_msg = f"❌ 切换模型失败: {str(e)}"
                    if chat_history:
                        chat_history.append(["", error_msg])
                    else:
                        chat_history = [["", error_msg]]
                    return chat_history
            return chat_history
        
        # 绑定模型切换事件
        model_selector.change(
            fn=switch_model,
            inputs=[model_selector, chatbot],
            outputs=[chatbot]
        )
        
        # 聊天功能
        def respond(message, chat_history, selected_model):
            """处理用户消息"""
            global last_diagnosis_response
            
            if not message.strip():
                return chat_history, ""
            
            # 第一步：立即显示用户消息，并显示"正在处理..."提示
            chat_history.append([message, "⏳ 正在处理中，请稍候..."])
            yield chat_history, ""
            
            # 第二步：获取诊断结果
            try:
                # 检查模型名称是否在映射中
                if selected_model not in MODEL_NAME_MAP:
                    error_msg = f"❌ 未知的模型选择: {selected_model}，请选择有效的模型"
                    print(f"[ERROR] {error_msg}")
                    if len(chat_history) > 0:
                        if isinstance(chat_history[-1], list) and len(chat_history[-1]) >= 2:
                            chat_history[-1][1] = error_msg
                        else:
                            chat_history[-1] = [message, error_msg]
                    else:
                        chat_history.append([message, error_msg])
                    yield chat_history, ""
                    return
                
                model_name = MODEL_NAME_MAP[selected_model]
                print(f"[DEBUG] ========== 处理用户消息 ==========")
                print(f"[DEBUG] 用户选择的模型: {selected_model} -> {model_name}")
                print(f"[DEBUG] 调用 init_orchestrator('{model_name}') 获取协调器...")
                current_orchestrator = init_orchestrator(model_name)
                print(f"[DEBUG] ✅ 协调器获取成功，开始诊断...")
                
                # 执行诊断（返回对话式文本）
                response = current_orchestrator.diagnose(message)
                
                # 确保response是字符串
                if not isinstance(response, str):
                    response = str(response)
                
                # 清理多余的空白字符
                response = response.strip()
                
                # 检查响应是否为空
                if not response or not response.strip():
                    response = "⚠️ 诊断返回了空响应，请检查日志。"
                    print("[ERROR] 诊断返回了空响应")
                
                last_diagnosis_response = response
                
                # 更新对话历史
                if len(chat_history) > 0:
                    if isinstance(chat_history[-1], list) and len(chat_history[-1]) >= 2:
                        chat_history[-1][1] = response
                    else:
                        chat_history[-1] = [message, response]
                else:
                    chat_history.append([message, response])
                
            except Exception as e:
                error_msg = f"❌ 发生错误: {str(e)}"
                last_diagnosis_response = error_msg
                print(f"[ERROR] {error_msg}")
                import traceback
                traceback.print_exc()
                
                if len(chat_history) > 0:
                    if isinstance(chat_history[-1], list) and len(chat_history[-1]) >= 2:
                        chat_history[-1][1] = error_msg
                    else:
                        chat_history[-1] = [message, error_msg]
                else:
                    chat_history.append([message, error_msg])
            
            # 第三步：返回完整的对话历史
            yield chat_history, ""
        
        # 文档导出功能
        def export_document(format_type: str):
            """导出文档并返回文件路径（用于浏览器下载）"""
            global last_diagnosis_response
            
            if not last_diagnosis_response or last_diagnosis_response.startswith("❌"):
                return None, "❌ 没有可导出的内容，请先与Agent对话获取分析结果"
            
            try:
                current_work_dir = os.getcwd()
                exports_dir = os.path.join(current_work_dir, "exports")
                os.makedirs(exports_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                if format_type == "word":
                    filename = f"multi_agent_report_{timestamp}.docx"
                    output_path = os.path.join(exports_dir, filename)
                    export_to_word(last_diagnosis_response, output_path)
                    status_msg = f"✅ Word文档已生成，请点击下方下载链接"
                    rel_path = os.path.relpath(output_path, current_work_dir)
                    return rel_path, status_msg
                else:  # pdf
                    filename = f"multi_agent_report_{timestamp}.pdf"
                    output_path = os.path.join(exports_dir, filename)
                    export_to_pdf(last_diagnosis_response, output_path)
                    status_msg = f"✅ PDF文档已生成，请点击下方下载链接"
                    rel_path = os.path.relpath(output_path, current_work_dir)
                    return rel_path, status_msg
            except Exception as e:
                return None, f"❌ 导出失败: {str(e)}"
        
        msg.submit(respond, [msg, chatbot, model_selector], [chatbot, msg])
        submit_btn.click(respond, [msg, chatbot, model_selector], [chatbot, msg])
        clear_btn.click(lambda: ([], ""), None, [chatbot, msg])
        
        # 绑定导出按钮
        export_word_btn.click(
            fn=lambda: export_document("word"),
            inputs=None,
            outputs=[export_file, export_status],
            js="""
            (file, status) => {
                if (file) {
                    setTimeout(() => {
                        // 查找文件下载链接并自动点击
                        const fileLinks = document.querySelectorAll('a[href*="multi_agent_report"]');
                        if (fileLinks.length > 0) {
                            fileLinks[fileLinks.length - 1].click();
                        } else {
                            // 备用方案：直接创建下载链接
                            const link = document.createElement('a');
                            link.href = file;
                            link.download = file.split('/').pop() || 'multi_agent_report.docx';
                            link.style.display = 'none';
                            document.body.appendChild(link);
                            link.click();
                            setTimeout(() => document.body.removeChild(link), 100);
                        }
                    }, 500);
                }
                return [file, status];
            }
            """
        )
        export_pdf_btn.click(
            fn=lambda: export_document("pdf"),
            inputs=None,
            outputs=[export_file, export_status],
            js="""
            (file, status) => {
                if (file) {
                    setTimeout(() => {
                        // 查找文件下载链接并自动点击
                        const fileLinks = document.querySelectorAll('a[href*="multi_agent_report"]');
                        if (fileLinks.length > 0) {
                            fileLinks[fileLinks.length - 1].click();
                        } else {
                            // 备用方案：直接创建下载链接
                            const link = document.createElement('a');
                            link.href = file;
                            link.download = file.split('/').pop() || 'multi_agent_report.pdf';
                            link.style.display = 'none';
                            document.body.appendChild(link);
                            link.click();
                            setTimeout(() => document.body.removeChild(link), 100);
                        }
                    }, 500);
                }
                return [file, status];
            }
            """
        )
        
        # 页面加载时立即更新一次
        demo.load(
            fn=update_monitoring_display,
            inputs=None,
            outputs=monitoring_html
        )
    
    return demo


def main():
    """主函数"""
    print("=" * 60)
    print("Hadoop 集群监控 Agent - Gradio Web 界面 (多智能体框架)")
    print("=" * 60)
    print()
    print("[INFO] 使用多智能体框架（分类→专家→讨论）")
    print("[INFO] 模式: vLLM（Qwen3-8B）")
    print()
    print("[提示] vLLM 配置：")
    print("[提示]   - 服务地址: http://10.157.197.76:8001/v1")
    print("[提示]   - 模型路径: /media/hnu/LLM/hnu/LLM/Qwen3-8B")
    print()
    print("[提示] 请确保 vLLM 服务已启动")
    print("-" * 60)
    print()
    print("[INFO] 正在预加载 Orchestrator...")
    print("[提示] 这可能需要一些时间，请耐心等待...")
    print("-" * 60)
    
    # 在启动时预加载 Orchestrator（使用默认模型 qwen-8b）
    try:
        init_orchestrator("qwen-8b")
        print("[INFO] Orchestrator 预加载完成（默认模型: Qwen3-8B）！")
    except Exception as e:
        print(f"[ERROR] Orchestrator 预加载失败: {e}")
        print()
        print("[错误] 无法启动 Orchestrator，请检查：")
        print("  1. vLLM 服务是否已启动")
        print("  2. 服务地址是否正确")
        print("  3. 模型路径是否正确")
        print()
        print("[提示] 可以运行以下命令检查 vLLM 服务：")
        print("  curl http://10.157.197.76:8001/health")
        print()
        print("[提示] 如果 vLLM 服务不可用，可以在界面中切换到其他模型（GPT-4o 或 DeepSeek-R1）")
        print()
    
    print()
    print("[INFO] 正在启动 Gradio 界面...")
    print("[INFO] 界面启动后，请在浏览器中打开显示的 URL")
    print("-" * 60)
    print()
    
    # 定义优雅关闭函数
    def graceful_shutdown(signum=None, frame=None):
        """优雅关闭 Gradio 服务器"""
        global demo_instance, _shutting_down
        
        if _shutting_down:
            os._exit(0)
            return
        
        _shutting_down = True
        print("\n[INFO] 收到中断信号，正在关闭服务器...") 
        
        import threading
        def close_demo():
            if demo_instance is not None:
                try:
                    demo_instance.close()
                    print("[INFO] Gradio 服务器已关闭")
                except Exception as e:
                    print(f"[WARNING] 关闭服务器时出错: {e}")
            import time
            time.sleep(0.1)
            os._exit(0)
        
        close_thread = threading.Thread(target=close_demo, daemon=True)
        close_thread.start()
        os._exit(0)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, graceful_shutdown)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, graceful_shutdown)
    
    try:
        # 创建界面
        demo = create_gradio_interface()
        global demo_instance
        demo_instance = demo
        
        # 启动界面
        current_work_dir = os.getcwd()
        exports_dir = os.path.join(current_work_dir, "exports")
        exports_dir_abs = os.path.abspath(exports_dir)
        os.makedirs(exports_dir_abs, exist_ok=True)
        
        print(f"[DEBUG] Gradio工作目录: {current_work_dir}")
        print(f"[DEBUG] Exports目录: {exports_dir_abs}")
        
        demo.launch(
            share=False,
            server_name="127.0.0.1",
            server_port=7860,
            show_error=True,
            allowed_paths=[exports_dir_abs, current_work_dir]
        )
    except KeyboardInterrupt:
        graceful_shutdown()
    except Exception as e:
        print(f"\n[ERROR] 启动失败: {e}")
        import traceback
        traceback.print_exc()
        graceful_shutdown()
        sys.exit(1)


if __name__ == "__main__":
    main()
