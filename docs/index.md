---
layout: home
hero:
  name: "我的心情库"
  text: "各种记不住的东西"
  tagline: "记录心情，沉淀生活"
  actions:
    - theme: brand
      text: 开始阅读
      link: /api/index
---

## ✍️ 关于作者

<!-- 1. 正常调用组件 -->
<VPTeamMembers :members="[
{
avatar: '/avatar.png',
name: '小大大',
title: '全栈开发工程师 / 文档作者',
desc: '热爱技术分享，追求极致代码优雅。',
links: [
{ icon: 'github', link: 'https://github.com' }
]
}
]" />

<!-- 2. 核心补丁：在 Markdown 中直接声明并引入官方组件 -->
<script setup>
import { VPTeamMembers } from 'vitepress/theme'
</script>
