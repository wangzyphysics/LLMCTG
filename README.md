# LLM中文文本生成系统 LLMCTG V1.0

本系统把原有的模型微调、分级内容生成和文本质量评分脚本整理为可安装、可配置、可测试的软件工程。系统支持小学、初中和高中三个阅读等级，既可使用内置演示生成器完成离线验收，也可接入本地 Hugging Face 因果语言模型。

## 快速体验

无需安装第三方依赖：

```bash
python -m llmctg demo --output output/demo
python -m llmctg evaluate --text "春天来了。小草从泥土里探出头。" --level primary
python -m llmctg generate --topic "海洋" --level junior --count 2 --output output/ocean.jsonl
```

批量任务使用 JSONL，每行至少包含 `topic`，可选字段为 `level`、`instruction` 和 `keywords`：

```bash
python -m llmctg batch --input examples/tasks.jsonl --output output/batch
```

使用本地大模型时安装可选依赖，并在配置文件中指定模型目录：

```bash
pip install -e ".[llm]"
python -m llmctg generate --backend transformers --model-path D:/models/Qwen --topic "人工智能" --level senior
```

加载微调生成的 LoRA 适配器：

```bash
python -m llmctg generate --backend transformers --model-path D:/models/Qwen --lora-path output/qwen-lora --topic "人工智能" --level senior
```

## 一键与分批功能测试

Linux 服务器上执行完整的一键测试（默认项目路径为
`/home/wangzy/workplace/wyc/llmctg`，模型路径为
`/home/wangzy/workplace/wyc/Qwen3-1.7B`）：

```bash
cd /home/wangzy/workplace/wyc/llmctg
CUDA_VISIBLE_DEVICES=0 python scripts/one_click_test.py
```

脚本会依次测试命令入口、配置生成、数据转换、模板生成、文本评估、批处理、
完整演示、本地模型生成、LoRA 微调和 LoRA 推理。每项执行前均显示预期结果，
最终在 `test_output/one_click_时间戳/` 中保存产物和 `test_summary.json`。

只测试不依赖本地大模型的功能：

```bash
python scripts/one_click_test.py --skip-llm
```

逐批测试请打开 `notebooks/llmctg_function_test.ipynb`，按单元格从上到下运行。


## 工程结构

- `src/llmctg`：系统源代码
- `tests`：自动化测试
- `examples`：输入示例与默认配置
- `scripts`：安装、演示和源码材料导出脚本
- `docs`：设计、测试、部署和登记说明
- `legacy`：原始脚本归档，仅用于迁移追溯，不作为运行入口

## 数据与隐私

默认模式完全离线，不向网络发送文本。模型模式只读取用户指定的本地模型。输入输出均为 UTF-8 编码，批处理采用逐行写入，异常任务会记录原因而不会中断整个批次。

## 权属提示

提交登记前应确认开发完成日期、首次发表状态等信息，并核对训练语料、模型、字词数据库及第三方组件的授权范围。本仓库中的第三方模型权重与原始数据不属于本软件源代码交付物。
