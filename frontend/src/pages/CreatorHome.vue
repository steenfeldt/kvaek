<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "../lib/api";
import { useSession } from "../stores/session";

const session = useSession();
const savedCount = ref<number | null>(null);

onMounted(async () => {
  const res = await api<{ saved_last_7_days: number }>("/creator/saved-count");
  savedCount.value = res.saved_last_7_days;
});
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 px-6 text-center">
    <h1 class="text-2xl font-semibold">{{ session.me?.display_name }}</h1>
    <p v-if="savedCount !== null" class="rounded-2xl bg-white p-6 text-lg shadow">
      {{ $t("creatorHome.savedCount", { count: savedCount }) }}
    </p>
    <p class="text-sm text-ink-600">{{ $t("creatorHome.notListed") }}</p>
  </main>
</template>
