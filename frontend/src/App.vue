<template>
  <div class="layout">
    <header class="topbar">
      <div class="brand">智策系统 · 医药智能分析</div>
      <nav class="nav">
        <RouterLink to="/">智能咨询</RouterLink>
        <RouterLink to="/diagnose">企业诊断</RouterLink>
        <RouterLink to="/risk">风险洞察</RouterLink>
        <RouterLink to="/report">分析报告</RouterLink>
      </nav>
    </header>
    <main class="page">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
</script>
