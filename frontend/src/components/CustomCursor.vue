<template>
  <div class="custom-cursor" :style="{ transform: `translate(${x}px, ${y}px)` }">
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
      <defs>
        <linearGradient id="cursor-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="#38bdf8" />
          <stop offset="1" stop-color="#818cf8" />
        </linearGradient>
      </defs>
      <path
        d="M4.5 2.5 L20.5 10.2 L12.6 12.2 L9.6 20.4 L4.5 2.5 Z"
        fill="url(#cursor-grad)"
        stroke="rgba(255,255,255,0.95)"
        stroke-width="1.4"
        stroke-linejoin="round"
      />
    </svg>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue"

const x = ref(-100)
const y = ref(-100)

const onMouseMove = (e) => {
  x.value = e.clientX - 1
  y.value = e.clientY - 1
}

onMounted(() => {
  document.body.classList.add("cursor-none")
  window.addEventListener("mousemove", onMouseMove)
})

onBeforeUnmount(() => {
  document.body.classList.remove("cursor-none")
  window.removeEventListener("mousemove", onMouseMove)
})
</script>

<style scoped>
.custom-cursor {
  position: fixed;
  left: 0;
  top: 0;
  pointer-events: none;
  z-index: 99999;
  will-change: transform;
  filter: drop-shadow(0 0 6px rgba(56, 189, 248, 0.95));
}
</style>
