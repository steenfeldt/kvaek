<script setup lang="ts">
import { ref } from "vue";

defineProps<{ text: string }>();

// Tooltips only open on hover/focus; a click toggle keeps it usable on touch.
const open = ref(false);
</script>

<template>
  <UTooltip v-model:open="open" :text="text" :delay-duration="0" :ui="{ content: 'max-w-xs h-auto py-2 whitespace-normal' }">
    <button
      type="button"
      class="flex h-5 w-5 items-center justify-center rounded-full border border-ink-300 text-xs font-medium text-ink-600 hover:border-clay-500 hover:text-clay-700"
      :aria-label="text"
      @click="open = !open"
    >
      ?
    </button>
  </UTooltip>
</template>
