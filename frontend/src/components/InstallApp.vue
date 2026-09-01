<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";

// Chromium fires beforeinstallprompt when the PWA is installable; Safari
// (iOS) has no install API, so there we can only show instructions.
const deferredPrompt = ref<{ prompt: () => Promise<void> } | null>(null);
const showIosHelp = ref(false);

const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent);
const standalone =
  window.matchMedia("(display-mode: standalone)").matches ||
  ("standalone" in navigator && (navigator as { standalone?: boolean }).standalone === true);

function onBeforeInstallPrompt(e: Event) {
  e.preventDefault();
  deferredPrompt.value = e as unknown as { prompt: () => Promise<void> };
}

onMounted(() => window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt));
onBeforeUnmount(() => window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt));

async function install() {
  await deferredPrompt.value?.prompt();
  deferredPrompt.value = null;
}
</script>

<template>
  <UCard v-if="!standalone && (deferredPrompt || isIos)">
    <h2 class="mb-1 font-semibold">{{ $t("install.title") }}</h2>
    <p class="mb-3 text-sm text-ink-600">{{ $t("install.hint") }}</p>
    <UButton v-if="deferredPrompt" @click="install">{{ $t("install.button") }}</UButton>
    <template v-else>
      <UButton v-if="!showIosHelp" variant="outline" color="neutral" @click="showIosHelp = true">
        {{ $t("install.button") }}
      </UButton>
      <p v-else class="text-sm">{{ $t("install.iosHelp") }}</p>
    </template>
  </UCard>
</template>
