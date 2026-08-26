<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "../lib/api";
import { kr } from "../lib/format";

interface Deal {
  id: number;
  campaign_name: string;
  counterpart_name: string;
  agreed_amount_ore: number;
  completed: boolean;
}

const deals = ref<Deal[]>([]);

onMounted(async () => {
  deals.value = await api<Deal[]>("/deals");
});
</script>

<template>
  <main class="mx-auto flex max-w-2xl flex-col gap-3 px-4 py-8">
    <h1 class="text-xl font-semibold">{{ $t("deals.title") }}</h1>
    <p v-if="!deals.length" class="text-ink-600">{{ $t("deals.empty") }}</p>
    <RouterLink
      v-for="d in deals"
      :key="d.id"
      :to="`/deals/${d.id}`"
      class="flex items-center justify-between rounded-xl bg-white p-4 shadow-sm hover:shadow"
    >
      <div>
        <span class="font-medium">{{ d.counterpart_name }}</span>
        <p class="text-sm text-ink-600">{{ d.campaign_name }}</p>
      </div>
      <div class="flex items-center gap-3 text-sm">
        <span class="text-ink-600">{{ $t("deals.agreed", { amount: kr(d.agreed_amount_ore) }) }}</span>
        <span v-if="d.completed" class="rounded-full bg-green-100 px-3 py-1 text-green-800">
          {{ $t("status.completed") }}
        </span>
      </div>
    </RouterLink>
  </main>
</template>
