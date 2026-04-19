<template>
  <div class="layout">
    <header class="topbar">
      <div class="brand">股票智能咨询智能体</div>
      <nav class="nav">
        <RouterLink to="/">智能咨询</RouterLink>
        <RouterLink to="/stock/600519">股票详情</RouterLink>
      </nav>
    </header>

    <main class="page">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
</script>
