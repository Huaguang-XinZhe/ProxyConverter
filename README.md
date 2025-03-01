# 代理转换器 (ProxyConverter)

这个工具用于从 YAML 配置文件中提取代理信息，并生成配置文件用于批量建立连接。目前支持 Hysteria2 类型的代理。

## 功能特点

- 从 YAML 文件中提取代理信息
- 生成 Hysteria2 客户端配置文件，支持动态端口分配
- 并发生成配置文件，提高效率
- 批量连接多个代理
- 使用服务器域名前缀作为配置文件名
- 支持显示节点名称

## 依赖项

使用前请确保安装以下依赖：

```bash
pip install pyyaml aiohttp
```

对于 Hysteria2 客户端功能，需要安装 [Hysteria2](https://hysteria.network/) 客户端。

## 使用方法

### 1. 提取代理信息

```bash
python main.py convert config.yaml
```

这将从 YAML 文件中提取所有 Hysteria2 代理，并生成配置文件。

### 2. 生成代理配置文件（指定输出目录）

```bash
python main.py convert config.yaml --output-dir ./configs
```

这将为所有 Hysteria2 代理生成配置文件，保存在 `./configs` 目录中。

### 3. 使用 Hysteria2 客户端连接单个代理

```bash
python main.py connect --config ./configs/代理名称.json
```

这将使用指定的配置文件启动 Hysteria2 客户端，在本地创建 HTTP 代理（地址在配置文件中指定）。

### 4. 批量连接多个代理

```bash
python main.py connect --batch --config-dir ./configs
```

这将批量连接 `./configs` 目录中的所有代理配置，并显示连接结果。

### 5. 批量连接时限制并发数量

```bash
python main.py connect --batch --config-dir ./configs --max-parallel 5
```

这将限制最大并发连接数为 5。

## 参数说明

### convert 命令

- `yaml_file`: YAML 配置文件路径，默认为 ./config.yaml
- `--type`, `-T`: 代理类型，默认为 hysteria2
- `--output-dir`, `-O`: 配置文件输出目录，默认为 ./configs

### connect 命令

- `--config`, `-C`: 单个配置文件路径，默认为 ./configs/1hk.json
- `--config-dir`, `-D`: 配置文件目录，用于批量连接，默认为 ./configs
- `--executable`, `-E`: Hysteria2 可执行文件路径
- `--batch`, `-B`: 批量连接模式
- `--limit`, `-L`: 限制批量连接的配置文件数量，0 表示不限制
- `--filter`, `-F`: 过滤配置文件的模式
- `--max-parallel`, `-M`: 最大并发数，0 表示不限制

## 示例工作流程

1. 从 YAML 文件中提取代理并生成配置文件：

```bash
python main.py convert config.yaml
```

2. 批量连接所有代理：

```bash
python main.py connect --batch
```

3. 过滤并连接特定代理：

```bash
python main.py connect --batch --filter hk
```

4. 连接到单个代理：

```bash
python main.py connect --config ./configs/hk1.json
```

## 新功能说明

1. **并发生成配置文件**：使用异步并发方式生成配置文件，大幅提高处理速度
2. **动态端口分配**：为每个配置文件预分配不同的 HTTP 端口
3. **节点名称支持**：配置文件中添加 name 字段，可以使用原始节点名称
4. **改进的中断处理**：优雅处理程序中断，确保所有资源正确清理

## 开发计划

1. 支持更多类型的代理
2. 添加 GUI 界面
