<template>
  <div id="app">
    <nav class="navbar">
      <div class="nav-brand">
        <span class="nav-icon">&#9881;</span>
        <span class="nav-title">设备预测性维护系统</span>
      </div>
      <div class="nav-links">
        <router-link to="/dashboard" class="nav-link">设备总览</router-link>
        <router-link to="/workorders" class="nav-link">维护工单</router-link>
      </div>
    </nav>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
</script>
