# 代理转换器 (ProxyConverter)

这个工具用于从 YAML 配置文件中提取代理信息，并生成配置文件用于批量建立连接。目前支持 Hysteria2 类型的代理。

## 功能特点

- 从 YAML 文件中提取代理信息
- 生成 Hysteria2 客户端配置文件，支持动态端口分配
- 并发生成配置文件，提高效率
- 批量连接多个代理
- 使用服务器域名前缀作为配置文件名
- 支持显示节点名称
- 支持随机选择代理
- 支持通过命令行直接指定过滤模式

## 依赖项

使用前请确保安装以下依赖：

```bash
pip install pyyaml aiofiles
```

对于 Hysteria2 客户端功能，需要安装 [Hysteria2](https://hysteria.network/) 客户端。

## 使用方法

### 基本用法

```bash
python main.py [参数]
```

### 参数说明

- `--yaml-file`, `-Y`: YAML 配置文件路径
- `--type`, `-T`: 代理类型，默认为 hysteria2
- `--output-dir`, `-O`: 配置文件输出目录，默认为 ./configs
- `--count`, `-C`: 随机选择的代理数量，默认为 5
- `--executable`, `-E`: Hysteria2 可执行文件路径
- `--filter`, `-F`: 配置文件过滤模式，支持正则表达式或以 | 分隔的多个文件名

### 使用示例

#### 1. 从 YAML 文件生成配置并随机选择 5 个代理连接

```bash
python main.py --yaml-file config.yaml
```

#### 2. 指定输出目录和随机选择数量

```bash
python main.py --yaml-file config.yaml --output-dir ./my_configs --count 10
```

#### 3. 使用过滤模式直接连接特定代理

```bash
python main.py --yaml-file config.yaml --filter "hk|sg"
```

这将连接文件名中包含 "hk" 或 "sg" 的所有代理。

#### 4. 使用正则表达式过滤

```bash
python main.py --yaml-file config.yaml --filter ".*-8080\.json"
```

这将连接所有使用 8080 端口的代理。

## 工作流程

1. 从 YAML 文件中提取代理信息
2. 生成配置文件，为每个代理分配唯一的 HTTP 端口
3. 保存端口范围信息到根目录的 proxy_ports.txt 文件
4. 如果指定了 --filter 参数，则直接使用该过滤模式连接代理
5. 否则，随机选择指定数量的代理并连接

## 过滤模式说明

过滤模式支持以下几种格式：

1. **单个文件名**：直接匹配文件名，如 `hk1-8080.json`
2. **多个文件名**：使用 | 分隔的多个文件名，精确匹配任意一个，如 `hk1-8080.json|sg1-8081.json`
3. **正则表达式**：匹配文件名的正则表达式，如 `hk.*\.json` 匹配所有以 hk 开头的 json 文件

## 新功能说明

1. **并发生成配置文件**：使用异步并发方式生成配置文件，大幅提高处理速度
2. **动态端口分配**：为每个配置文件预分配不同的 HTTP 端口
3. **节点名称支持**：配置文件中添加 name 字段，可以使用原始节点名称
4. **改进的中断处理**：优雅处理程序中断，确保所有资源正确清理
5. **命令行过滤模式**：可以直接通过命令行指定过滤模式，无需随机选择

## 开发计划

1. 支持更多类型的代理
2. 添加 GUI 界面
