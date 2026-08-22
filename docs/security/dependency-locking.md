# Python 依赖锁定与更新流程

## 目标与边界

OIN 的 `pyproject.toml` 仍是**人类维护的兼容性声明**；`requirements*.lock` 是针对 Python 3.11 生成的、带 SHA-256 分发包哈希的解析结果。两者分开可以在不把每一个传递依赖写入项目元数据的前提下，使开发、演示和容器构建使用可审查的精确版本。

| 文件 | 用途 | 是否应手工编辑 |
| --- | --- | --- |
| `pyproject.toml` | 运行时、可选开发依赖和构建后端的意图声明 | 是；修改后必须重新生成锁文件。 |
| `requirements-build.in` | 本地项目构建后端的最小输入 | 是；必须与 `[build-system].requires` 保持兼容。 |
| `requirements-build.lock` | 受哈希保护的构建后端版本 | 否；由 `uv pip compile` 生成。 |
| `requirements.lock` | 受哈希保护的 Python 3.11 运行时解析结果 | 否；由 `uv pip compile` 生成。 |
| `requirements-dev.lock` | 运行时加 `dev` extra 的受哈希保护解析结果 | 否；由 `uv pip compile` 生成。 |

pip 的哈希校验模式要求所有依赖均被精确固定并带本地哈希；缺少任何传递依赖或哈希都会失败，而不是回退到未受约束的下载。[1] OIN 随后以 `pip install --no-deps` 安装本地项目，避免项目安装阶段重新解析未锁定的依赖。[1]

## 安装

开发环境以构建锁、开发锁和无依赖本地安装的顺序建立：

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements-build.lock
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
```

容器构建使用相同原则：先安装 `requirements-build.lock` 与 `requirements.lock`，然后以 `--no-deps --no-build-isolation` 安装项目。这样，Docker 构建不会在解析 `>=` 约束时选择新的传递版本。

> 锁文件不能证明发行包本身没有恶意代码、不能替代漏洞扫描，也不能消除 Python 版本、系统库或容器基础镜像差异。它们只把“本次允许下载哪些已知分发包”变成可复核的输入。

## 受控更新

更新不是日常构建步骤。只有在审查变更、测试和记录风险后才可执行下列命令。默认 `uv pip compile` 会尊重已存在锁文件中的版本；全量升级必须显式加 `--upgrade`，单包升级必须显式加 `--upgrade-package`。[2]

```bash
# 在修改 pyproject.toml 或 requirements-build.in 后重新解析。
uv pip compile requirements-build.in --python-version 3.11 --generate-hashes \
  --output-file requirements-build.lock
uv pip compile pyproject.toml --python-version 3.11 --generate-hashes \
  --output-file requirements.lock
uv pip compile pyproject.toml --extra dev --python-version 3.11 --generate-hashes \
  --output-file requirements-dev.lock

# 审查每个固定版本与哈希，然后验证。
python -m pip install --require-hashes -r requirements-build.lock
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
ruff check oin network-demo/tools/operator.py network-demo/tests/test_network_demo.py tests
pytest -q tests
```

任何涉及 `cryptography` 的版本变化都必须额外检查签名、离线验证和跨实现测试；它不是签名算法变更，但仍属于高影响供应链变动。不要在锁定更新中顺带改变 Ed25519、SHA-256、身份锚定或历史验签语义。

## 审查清单

| 检查 | 通过条件 |
| --- | --- |
| 完整性 | 每个 `*.lock` 内的每个包均为 `==` 固定版本并带 `--hash=sha256:`。 |
| 声明一致性 | `requirements-build.in` 与 `pyproject.toml` 的构建后端要求兼容；开发锁含 `dev` extra。 |
| 安装行为 | 新虚拟环境在 `--require-hashes` 与 `--no-deps` 下成功安装。 |
| 运行行为 | `ruff` 与完整主测试均通过。 |
| 发布边界 | Dockerfile 仅复制锁文件后安装受锁定依赖，再复制源码并以无依赖模式安装。 |
| 更新记录 | 版本变动、理由、测试结果和已知漏洞结论在提交或安全审计中可追溯。 |

## References

[1]: https://pip.pypa.io/en/stable/topics/secure-installs/ "pip Secure installs"
[2]: https://docs.astral.sh/uv/pip/compile/ "uv Locking environments"
