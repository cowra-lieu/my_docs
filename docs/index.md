---
layout: home
hero:
  name: "我的备忘录"
  text: "忘得太快，时不时拿出来翻翻"
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
avatar: 'avatar.png',
name: '小大大',
title: '顺其自然 / 好好活着',
desc: '各种东西，越来越记不住。',
links: [
{ icon: 'github', link: 'https://github.com' }
]
}
]" />

<!-- 2. 核心补丁：在 Markdown 中直接声明并引入官方组件 -->
<script setup>
import { VPTeamMembers } from 'vitepress/theme'
</script>
