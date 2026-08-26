<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { api } from "../lib/api";
import { useSession } from "../stores/session";

const session = useSession();
const { data } = useQuery({
  queryKey: ["saved-count"],
  queryFn: () => api<{ saved_last_7_days: number }>("/creator/saved-count"),
});
</script>

<template>
  <main class="mx-auto flex max-w-md flex-col gap-6 px-6 pt-12 text-center">
    <h1 class="text-2xl font-semibold">{{ session.me?.display_name }}</h1>
    <UCard v-if="data">
      <p class="text-lg">{{ $t("creatorHome.savedCount", { count: data.saved_last_7_days }) }}</p>
    </UCard>
  </main>
</template>
