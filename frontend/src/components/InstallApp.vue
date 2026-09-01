<script setup lang="ts">
import { ref } from "vue";
import { installPrompt } from "../lib/install";

const showHelp = ref(false);

const ua = navigator.userAgent;
// iPadOS Safari reports a Macintosh UA; touch points tell it apart.
const isIos = /iphone|ipad|ipod/i.test(ua) || (/macintosh/i.test(ua) && navigator.maxTouchPoints > 1);
const isMacSafari =
  /macintosh/i.test(ua) && /safari/i.test(ua) && !/chrome|chromium|edg|firefox/i.test(ua) && !isIos;
const standalone =
  window.matchMedia("(display-mode: standalone)").matches ||
  ("standalone" in navigator && (navigator as { standalone?: boolean }).standalone === true);

async function install() {
  await installPrompt.value?.prompt();
  installPrompt.value = null;
}
</script>

<template>
  <UCard v-if="!standalone && (installPrompt || isIos || isMacSafari)">
    <h2 class="mb-1 font-semibold">{{ $t("install.title") }}</h2>
    <p class="mb-3 text-sm text-ink-600">{{ $t("install.hint") }}</p>
    <UButton v-if="installPrompt" @click="install">{{ $t("install.button") }}</UButton>
    <template v-else>
      <UButton v-if="!showHelp" variant="outline" color="neutral" @click="showHelp = true">
        {{ $t("install.button") }}
      </UButton>
      <p v-else class="text-sm">{{ isIos ? $t("install.iosHelp") : $t("install.macHelp") }}</p>
    </template>
  </UCard>
</template>
