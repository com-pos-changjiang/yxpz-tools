## 客户端使用

### 1 Windows 客户端配置（推荐）

Windows 环境下创建 `pip.ini` 配置文件，一次配置永久生效：

**配置文件位置**：

```
C:\Users\你的用户名\pip\pip.ini
```

**创建步骤**（CMD 或 PowerShell）：

```cmd
# 创建 pip 目录（如果不存在）
mkdir %USERPROFILE%\pip

# 创建配置文件
notepad %USERPROFILE%\pip\pip.ini
```

**配置内容**（替换实际 IP 和密码）：

```ini
[global]
index-url = http://<用户名>:<密码>@20.58.32.156:28080/simple
trusted-host = 20.58.32.156
```

**配置说明**：

| 参数             | 说明                                          |
|----------------|---------------------------------------------|
| `index-url`    | 包含账号密码的完整地址，格式：`http://用户名:密码@IP:端口/simple` |
| `trusted-host` | 信任的服务器 IP（防止 HTTPS 警告）                      |

**使用示例**（配置后直接使用）：

```cmd
# 不需要再输入账号密码
pip install DrssionPage
pip install -r requirements.txt

# 查看当前配置
pip config list
```

### 2 Linux/Mac 客户端配置

创建或编辑 `~/.pip/pip.conf`:

```ini
[global]
index-url = http://<用户名>:<密码>@20.58.32.156:28080/simple
trusted-host = 20.58.32.156
```

或使用环境变量：

```bash
export PIP_INDEX_URL="http://<用户名>:<密码>@20.58.32.156:28080/simple"

# 添加到 ~/.bashrc 永久生效
echo 'export PIP_INDEX_URL="http://<用户名>:<密码>@20.58.32.156:28080/simple"' >> ~/.bashrc
source ~/.bashrc
```

### 3 临时指定（不推荐）

```bash
# 临时使用，不需要配置文件
pip install package-name --index-url http://<用户名>:<密码>@20.58.32.156:28080/simple

pip install yxpz_tools --index-url http://<用户名>:<密码>@20.58.32.156:28081/simple --trusted-host 20.58.32.156
pip install yxpz_tools --index-url http://<用户名>:<密码>@20.58.32.156:28080/simple --trusted-host=20.58.32.156

```

### 4 直接修改配置的命令（windows和linux都可用）

在命令行执行，本质还是修改 pip.ini 文件内容

```bash
pip config set global.index-url  http://<用户名>:<密码>@20.58.32.156:28080/simple
#查看所有配置
pip config debug

pip config set global.index-url  http://<用户名>:<密码>@20.58.32.156:28080/simple
pip config set global.trusted-host 20.58.32.156
```
