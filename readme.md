## 整体工作流
[本地编辑 MD] ──(git push)──> [GitHub 仓库] ──(GitHub Actions 自动构建)──> [GitHub Pages 公网访问]

## 本地目录结构
```
my-docs/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions 自动化部署脚本
├── docs/                       # 你的 Markdown 文档全部放在这里
│   ├── .vitepress/
│   │   └── config.mts          # VitePress 核心配置文件
│   ├── index.md                # 网站首页
│   ├── guide/                  # 分类目录 A
│   │   ├── get-started.md
│   │   └── advanced.md
│   └── api/                    # 分类目录 B
│       ├── index.md
│       └── reference.md
├── package.json                # 项目依赖配置
└── vite.config.ts              # Vite 插件配置（用于自动生成侧边栏）
```





