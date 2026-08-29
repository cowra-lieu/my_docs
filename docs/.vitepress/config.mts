// VitePress 的核心配置文件。在这里启用自动侧边栏插件：
import { defineConfig } from 'vitepress'
import { withSidebar } from 'vitepress-sidebar'
import mathjax3 from 'markdown-it-mathjax3'

export default withSidebar(
    defineConfig({
        title: "我的备忘录",
        description: "优雅的 Markdown 自动化文档",
        // 如果你的 GitHub Pages 网址是 https://<username>.github.io/<repo>/，请解除下一行的注释并填写仓库名
        // base: '/<repo>/',
        base: '/my_docs/',

        // 1. 开启全局的最后更新时间计算功能（基于 Git 提交记录）
        lastUpdated: true,

        markdown: {
            config: (md) => {
                md.use(mathjax3 as any)
            }
        },

        themeConfig: {
            // 💡 核心添加：开启右侧大纲导航
            outline: {
                level: [2, 3],        // 提取哪些层级的标题？[2, 3] 表示只提取 ## 和 ###。如果想提取更深，可以写 [2, 6]
                label: '本页目录'     // 右侧大纲的顶部提示文字（汉化）
            },

            // 2. 自定义最后更新时间的显示文本和格式
            lastUpdated: {
                text: '最后更新于',
                formatOptions: {
                    dateStyle: 'short',   // 显示格式如: 2026/08/15
                    timeStyle: 'medium'   // 显示格式如: 10:00:00
                }
            },

            docFooter: {
                prev: '上一篇',
                next: '下一篇'
            },

            search: {
                provider: 'local',
                options: {
                    translations: {
                        button: { buttonText: '搜索文档' },
                        modal: {
                            noResultsText: '无法找到相关结果',
                            resetButtonTitle: '清除查询条件',
                            footer: { selectText: '选择', navigateText: '切换', closeText: '关闭' }
                        }
                    }
                }
            },

            nav: [
                { text: '首页', link: '/' },
                { text: '指南', link: '/guide/get-started' }
            ],

            socialLinks: [
                { icon: 'github', link: 'https://github.com' }
            ]
        }
    }),

    // ✅ 新插件的侧边栏配置写在这里（作为 withSidebar 的第二个参数）
    {
        documentRootPath: 'docs',
        collapseDepth: 2,
        capitalizeFirst: true,
        // 1. 核心保留：确保菜单里能明确看到并点击 Index 项
        includeFolderIndexFile: true,

        // 2. 联动开关：当点击目录展开/收起时，不会强行霸占路由链接
        useIndexFileForFolder: true,

        // 3. 【解决冲突的关键】将目录本身变成纯链接，把展开/收起功能交给右侧的小箭头
        hyphenToSpace: true,
        keepMarkdownSyntaxFromTitle: true,

        // 4. 高级配置：如果想让目录拥有点击链接的能力，建议配置默认折叠状态
        collapsed: true,                           // 让目录默认折叠，逼使它渲染出切换箭头
        scanStartPath: null,
        resolveAutoItemLink: true
    } as any
)
