<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api } from "../lib/api";

const route = useRoute();
const id = route.params.id as string;
const attempts = ref(0);

const { data } = useQuery({
  queryKey: ["campaign", id, "payment-poll"],
  queryFn: () => {
    attempts.value += 1;
    return api<{ status: string }>(`/campaigns/${id}`);
  },
  refetchInterval: (query) => (query.state.data?.status === "active" ? false : 2500),
});

const state = computed<"waiting" | "success" | "failed">(() => {
  if (data.value?.status === "active") return "success";
  return attempts.value >= 12 ? "failed" : "waiting";
});
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
      <UButton :to="`/campaigns/${id}`" size="lg">{{ $t("payment.toCampaign") }}</UButton>
    </template>
    <template v-else>
      <p class="text-lg font-medium">{{ $t("payment.failed") }}</p>
      <UButton :to="`/campaigns/${id}`" variant="outline" color="neutral" size="lg">
        {{ $t("payment.retry") }}
      </UButton>
    </template>
  </main>
</template>
