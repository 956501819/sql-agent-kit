<template>
  <div class="app">
    <header class="header">
      <div class="logo">SQL Agent Kit</div>
      <nav class="nav">
        <router-link
          v-for="route in navRoutes"
          :key="route.path"
          :to="route.path"
          class="nav-item"
          active-class="nav-item--active"
        >
          <span class="nav-icon">{{ route.meta.icon }}</span>
          <span class="nav-label">{{ route.meta.label }}</span>
        </router-link>
      </nav>
    </header>
    <main class="main">
      <router-view v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
const navRoutes = router.getRoutes().filter(r => r.meta?.label)
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #f5f6fa;
  color: #1a1a2e;
  font-size: 14px;
}

.app { display: flex; flex-direction: column; min-height: 100vh; }

.header {
  background: #1a1a2e;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 0 24px;
  height: 52px;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,.3);
}

.logo {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: .5px;
  white-space: nowrap;
  color: #7c83fd;
}

.nav { display: flex; gap: 2px; overflow-x: auto; }

.nav-item {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border-radius: 6px;
  color: rgba(255,255,255,.7);
  text-decoration: none;
  font-size: 13px;
  white-space: nowrap;
  transition: background .15s, color .15s;
}
.nav-item:hover { background: rgba(255,255,255,.1); color: #fff; }
.nav-item--active { background: #7c83fd; color: #fff; }

.nav-icon { font-size: 14px; }

.main { flex: 1; padding: 24px; max-width: 1200px; width: 100%; margin: 0 auto; }

/* Shared utility classes */
.card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
  margin-bottom: 16px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: opacity .15s, transform .1s;
}
.btn:active { transform: scale(.97); }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn--primary { background: #7c83fd; color: #fff; }
.btn--primary:hover:not(:disabled) { background: #6970e8; }
.btn--danger  { background: #ff4d4f; color: #fff; }
.btn--danger:hover:not(:disabled)  { background: #e03e40; }
.btn--ghost   { background: transparent; border: 1px solid #d9d9d9; color: #555; }
.btn--ghost:hover:not(:disabled)   { border-color: #7c83fd; color: #7c83fd; }
.btn--sm { padding: 5px 12px; font-size: 12px; }

.input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color .15s;
}
.input:focus { border-color: #7c83fd; }

.textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  font-family: 'Menlo', 'Consolas', monospace;
  resize: vertical;
  outline: none;
  transition: border-color .15s;
}
.textarea:focus { border-color: #7c83fd; }

.label { font-size: 13px; font-weight: 600; color: #555; margin-bottom: 6px; display: block; }

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}
.tag--success { background: #f0fff4; color: #22863a; }
.tag--error   { background: #fff0f0; color: #cf1322; }
.tag--warn    { background: #fffbe6; color: #d48806; }
.tag--info    { background: #e8f4fd; color: #0969da; }

.section-title {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 16px;
  color: #1a1a2e;
}

.alert {
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 13px;
  margin-top: 8px;
}
.alert--success { background: #f0fff4; color: #22863a; border: 1px solid #b7ebc8; }
.alert--error   { background: #fff0f0; color: #cf1322; border: 1px solid #ffc1c1; }
.alert--warn    { background: #fffbe6; color: #d48806; border: 1px solid #ffe58f; }
</style>
