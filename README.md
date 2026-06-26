# Chainlit 中文文档

本仓库是 [Chainlit/docs](https://github.com/Chainlit/docs) 的 fork，提供**纯中文**文档站点，并采用**按需翻译**维护模型。

> **重要**：`docs.json` 由脚本自动生成，请勿手改。修改导航或路由请编辑 `i18n/` 下的配置文件并重新运行 `apply_zh_site.py`。

官方英文文档：[https://docs.chainlit.io](https://docs.chainlit.io)

## 仓库结构

| 路径 | 说明 |
|------|------|
| 根目录 `**/*.mdx` | **英文源文件**（来自 upstream merge，禁止手改） |
| `zh/**` | **中文译文**（唯一允许手改的内容区） |
| `i18n/upstream-navigation.json` | 从 upstream `docs.json` 提取的导航快照 |
| `i18n/site-zh.json` | 中文站点 overlay（站点名、Tab/Group 中文标签、navbar） |
| `i18n/docs-base.json` | 主题、颜色、logo 等非导航配置 |
| `.translation-lock.json` | 每页翻译状态（synced / missing / outdated） |
| `scripts/` | 维护脚本（标准库 Python） |
| `en-version-link.js` / `.css` | 每页自动注入「查看英文原文」链接（Mintlify 全站加载） |

## 英文原文链接

站点通过 `en-version-link.js` 在顶部导航栏 Github 链接左侧注入「英文原文」，指向 [docs.chainlit.io](https://docs.chainlit.io) 对应当前页面的英文版。路径规则：当前 URL 去掉 `zh/` 前缀即为英文站 slug。

## 页面路由策略

| lock 状态 | docs.json 中的路径 |
|-----------|-------------------|
| `synced` | `zh/foo/bar`（中文正文） |
| `missing` | `foo/bar`（英文回退） |
| `outdated` | `foo/bar`（英文回退，避免展示过期译文） |

导航结构始终与 upstream 一致；仅页面路径在 `zh/` 与根目录间切换。

## 本地开发

```bash
npx mint dev
```

## 维护工作流

### 1. 同步 upstream

```bash
git remote add upstream https://github.com/Chainlit/docs.git   # 首次
git fetch upstream main
git merge upstream/main --no-edit
python scripts/copy_upstream_nav.py
python scripts/translation_status.py --since-merge --report
python scripts/apply_zh_site.py
```

若 `translation-report.md` 无 missing/outdated 条目，可直接合并 sync PR。

### 2. 翻译页面

```bash
# 1. 编辑或新建 zh/ 下对应 MDX
# 2. 标记为已翻译
python scripts/translation_status.py --mark-translated zh/get-started/overview.mdx
# 3. 重新生成 docs.json
python scripts/apply_zh_site.py
```

### 3. 常用命令

```bash
# 全量扫描所有英文 MDX，更新 lock
python scripts/translation_status.py --all --report

# 校验 lock 与 zh 文件一致性
python scripts/translation_status.py --validate

# 从当前 docs.json 提取导航（bootstrap / 冲突恢复）
python scripts/copy_upstream_nav.py

# 生成 docs.json
python scripts/apply_zh_site.py
```

## CI

- **sync-upstream.yml**：每周一 + 手动触发，检测 upstream 更新并自动开 PR（含 `translation-report.md`）
- **check-translations.yml**：PR 中修改 `zh/**` 时必须同步更新 `.translation-lock.json`

## 发布

推送到默认分支后，Mintlify 会自动部署到生产环境。PR 会生成预览链接。

#### 故障排查

参见 [Mintlify 文档](https://mintlify.com/docs/quickstart#troubleshooting)。
