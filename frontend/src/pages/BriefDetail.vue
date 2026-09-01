<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { api } from "../lib/api";
import { kr } from "../lib/format";
import { statusColor } from "../lib/status";

interface Proposal {
  id: number;
  round: number;
  author: string;
  amount_ore: number;
  message: string;
  status: string;
}
interface BriefDetail {
  id: number;
  creator_name: string;
  campaign_name: string;
  brand_name: string;
  message: string;
  status: string;
  my_side: string;
  proposals: Proposal[];
  can_propose: boolean;
  can_accept: boolean;
  can_decline: boolean;
  deal_id: number | null;
}

const route = useRoute();
const id = route.params.id as string;
const queryClient = useQueryClient();

const { data: brief } = useQuery({
  queryKey: ["brief", id],
  queryFn: () => api<BriefDetail>(`/briefs/${id}`),
});

const amountKr = ref<number | null>(null);
const proposalMessage = ref("");
const error = ref("");

const openProposal = computed(() => brief.value?.proposals.find((p) => p.status === "open") ?? null);

function refresh() {
  queryClient.invalidateQueries({ queryKey: ["brief", id] });
  queryClient.invalidateQueries({ queryKey: ["briefs"] });
  queryClient.invalidateQueries({ queryKey: ["deals"] });
}

function makeMutation(fn: () => Promise<unknown>) {
  return useMutation({
    mutationFn: fn,
    onSuccess: refresh,
    onError: (e) => (error.value = e.message),
  });
}

const proposeMutation = makeMutation(() =>
  api(`/briefs/${id}/proposals`, {
    method: "POST",
    body: JSON.stringify({
      amount_ore: Math.round((amountKr.value ?? 0) * 100),
      message: proposalMessage.value,
    }),
  }),
);
const acceptMutation = makeMutation(() => api(`/briefs/${id}/accept`, { method: "POST" }));
const declineMutation = makeMutation(() => api(`/briefs/${id}/decline`, { method: "POST" }));
</script>

<template>
  <main v-if="brief" class="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
    <UCard>
      <div class="flex items-center justify-between">
        <h1 class="text-lg font-semibold">
          {{ brief.my_side === "brand" ? brief.creator_name : brief.brand_name }}
        </h1>
        <UBadge :color="statusColor(brief.status)" variant="subtle">{{ $t(`status.${brief.status}`) }}</UBadge>
      </div>
      <p class="mt-1 text-sm text-ink-600">{{ brief.campaign_name }}</p>
      <p class="mt-3 whitespace-pre-wrap">{{ brief.message }}</p>
    </UCard>

    <UCard>
      <h2 class="mb-1 text-lg font-semibold">{{ $t("brief.negotiation") }}</h2>
      <p class="mb-4 text-sm text-ink-600">{{ $t("brief.youAre", { side: $t(`brief.${brief.my_side}`) }) }}</p>

      <ol class="flex flex-col gap-3">
        <li
          v-for="p in brief.proposals"
          :key="p.id"
          class="rounded-xl border border-clay-200 p-4"
          :class="p.author === brief.my_side ? 'ml-8 bg-clay-50' : 'mr-8'"
        >
          <div class="flex items-center justify-between text-sm text-ink-600">
            <span>{{ $t("brief.round", { round: p.round }) }} · {{ $t(`brief.${p.author}`) }}</span>
            <UBadge v-if="p.status !== 'open'" :color="statusColor(p.status)" variant="subtle" size="sm">
              {{ $t(`status.${p.status}`) }}
            </UBadge>
          </div>
          <p class="mt-1 text-xl font-semibold">{{ kr(p.amount_ore) }}</p>
          <p v-if="p.message" class="mt-1 text-sm">{{ p.message }}</p>
        </li>
      </ol>

      <form v-if="brief.can_propose" class="mt-4 flex flex-col gap-3" @submit.prevent="proposeMutation.mutate()">
        <UFormField :label="$t('brief.amountKr')" required>
          <UInput v-model.number="amountKr" type="number" min="1" step="1" required class="w-full" />
        </UFormField>
        <UFormField :label="$t('brief.proposalMessage')">
          <UTextarea v-model="proposalMessage" :rows="2" class="w-full" />
        </UFormField>
        <UButton type="submit" :loading="proposeMutation.isPending.value" block>
          {{ $t("brief.submitProposal") }}
        </UButton>
      </form>

      <div class="mt-4 flex gap-3">
        <UButton
          v-if="brief.can_accept && openProposal"
          color="success"
          size="lg"
          class="flex-1 justify-center"
          :loading="acceptMutation.isPending.value"
          @click="acceptMutation.mutate()"
        >
          {{ $t("brief.accept", { amount: kr(openProposal.amount_ore) }) }}
        </UButton>
        <UButton
          v-if="brief.can_decline"
          variant="outline"
          color="neutral"
          size="lg"
          :loading="declineMutation.isPending.value"
          @click="declineMutation.mutate()"
        >
          {{ $t("brief.decline") }}
        </UButton>
      </div>

      <p
        v-if="!brief.can_propose && !brief.can_accept && ['sent', 'negotiating'].includes(brief.status)"
        class="mt-4 text-sm text-ink-600"
      >
        {{ $t("brief.waiting") }}
      </p>

      <UButton v-if="brief.deal_id" :to="`/deals/${brief.deal_id}`" size="lg" block class="mt-4">
        {{ $t("brief.goToChat") }}
      </UButton>
    </UCard>

    <UAlert v-if="error" color="error" variant="outline" class="bg-white" :description="error" />
  </main>
</template>
