<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api } from "../lib/api";

const route = useRoute();
const id = route.params.id as string;
const state = ref<"waiting" | "success" | "failed">("waiting");
let timer: ReturnType<typeof setInterval> | undefined;
let attempts = 0;

async function poll() {
  attempts += 1;
  try {
    const campaign = await api<{ status: string }>(`/campaigns/${id}`);
    if (campaign.status === "active") {
      state.value = "success";
      clearInterval(timer);
    } else if (attempts >= 12) {
      state.value = "failed";
      clearInterval(timer);
    }
  } catch {
    if (attempts >= 12) {
      state.value = "failed";
      clearInterval(timer);
    }
  }
}

onMounted(() => {
  poll();
  timer = setInterval(poll, 2500);
});
onUnmounted(() => clearInterval(timer));
</script>

<template>
  <main class="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center gap-4 px-6 text-center">
    <template v-if="state === 'waiting'">
      <div class="h-10 w-10 animate-spin rounded-full border-4 border-clay-200 border-t-clay-600" />
      <p class="text-ink-600">{{ $t("payment.waiting") }}</p>
    </template>
    <template v-else-if="state === 'success'">
      <p class="text-4xl">🎉</p>
      <p class="text-lg font-medium">{{ $t("payment.success") }}</p>
      <RouterLink :to="`/campaigns/${id}`" class="rounded-lg bg-clay-600 px-6 py-3 text-white">
        {{ $t("payment.toCampaign") }}
      </RouterLink>
    </template>
    <template v-else>
      <p class="text-lg font-medium">{{ $t("payment.failed") }}</p>
      <RouterLink :to="`/campaigns/${id}`" class="rounded-lg border border-clay-200 px-6 py-3">
        {{ $t("payment.retry") }}
      </RouterLink>
    </template>
  </main>
</template>
