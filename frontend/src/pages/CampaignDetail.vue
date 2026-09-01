<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { api } from "../lib/api";
import { kr } from "../lib/format";
import { statusColor } from "../lib/status";

interface Brief {
  id: number;
  creator_id: number;
  creator_name: string;
  status: string;
}
interface Campaign {
  id: number;
  name: string;
  description: string;
  tier: string;
  status: string;
  briefs_total: number;
  briefs_used: number;
  briefs: Brief[];
  invoice_id: number | null;
  invoice_number: number | null;
}
interface Tier {
  tier: string;
  price_ore: number;
  price_incl_vat_ore: number;
  briefs: number;
}
interface Card {
  id: number;
  display_name: string;
  city: string;
}
interface Shortlist {
  id: number;
  name: string;
  count: number;
}

const route = useRoute();
const id = route.params.id as string;
const queryClient = useQueryClient();

const { data: campaign } = useQuery({
  queryKey: ["campaign", id],
  queryFn: () => api<Campaign>(`/campaigns/${id}`),
});

const { data: tiers } = useQuery({ queryKey: ["tiers"], queryFn: () => api<Tier[]>("/tiers"), staleTime: Infinity });
const grossAmount = computed(() => {
  const t = tiers.value?.find((t) => t.tier === campaign.value?.tier);
  return t ? t.price_incl_vat_ore : null;
});

const { data: shortlisted } = useQuery({
  queryKey: ["shortlisted-creators"],
  queryFn: async () => {
    const lists = await api<Shortlist[]>("/shortlists");
    const cards = await Promise.all(lists.map((l) => api<Card[]>(`/shortlists/${l.id}`)));
    const seen = new Set<number>();
    return cards.flat().filter((c) => (seen.has(c.id) ? false : (seen.add(c.id), true)));
  },
});

const available = computed(() => {
  if (!campaign.value || !shortlisted.value) return [];
  const briefed = new Set(campaign.value.briefs.map((b) => b.creator_id));
  return shortlisted.value.filter((c) => !briefed.has(c.id));
});

const quotaLeft = computed(() =>
  campaign.value ? campaign.value.briefs_total - campaign.value.briefs_used : 0,
);

const message = ref("");
const error = ref("");

const payMutation = useMutation({
  mutationFn: () =>
    api<{ checkout_url: string }>(`/campaigns/${id}/checkout`, { method: "POST" }),
  onSuccess: (res) => {
    if (res.checkout_url) window.location.href = res.checkout_url;
    else queryClient.invalidateQueries({ queryKey: ["campaign", id] });
  },
  onError: (e) => (error.value = e.message),
});

const briefMutation = useMutation({
  mutationFn: (creatorId: number) =>
    api(`/campaigns/${id}/briefs`, {
      method: "POST",
      body: JSON.stringify({ creator_id: creatorId, message: message.value }),
    }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["campaign", id] });
    queryClient.invalidateQueries({ queryKey: ["briefs"] });
  },
  onError: (e) => (error.value = e.message),
});
</script>

<template>
  <main v-if="campaign" class="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
    <UCard>
      <div class="flex items-center justify-between">
        <h1 class="text-xl font-semibold">{{ campaign.name }}</h1>
        <UBadge :color="statusColor(campaign.status)" variant="subtle">{{ $t(`status.${campaign.status}`) }}</UBadge>
      </div>
      <p class="mt-2 text-ink-600">{{ campaign.description }}</p>
      <p v-if="campaign.status === 'active'" class="mt-2 text-sm text-ink-600">
        {{ $t("campaigns.briefsUsed", { used: campaign.briefs_used, total: campaign.briefs_total }) }}
      </p>
      <template v-if="campaign.status === 'draft'">
        <UButton
          :loading="payMutation.isPending.value"
          size="lg"
          block
          class="mt-4"
          @click="payMutation.mutate()"
        >
          {{ $t("campaigns.payActivate") }}
        </UButton>
        <p v-if="grossAmount" class="mt-2 text-center text-sm text-ink-600">
          {{ $t("campaigns.totalInclVat", { amount: kr(grossAmount) }) }}
        </p>
      </template>
      <a
        v-if="campaign.invoice_id"
        :href="`/api/invoices/${campaign.invoice_id}/pdf`"
        class="mt-3 block text-sm text-fjord-700 underline"
      >
        {{ $t("campaigns.invoiceDownload", { number: campaign.invoice_number }) }}
      </a>
    </UCard>

    <UCard v-if="campaign.status === 'active' && quotaLeft > 0">
      <h2 class="mb-3 text-lg font-semibold">{{ $t("campaigns.sendBriefs") }}</h2>
      <p v-if="!available.length" class="text-ink-600">{{ $t("campaigns.noShortlisted") }}</p>
      <template v-else>
        <UTextarea v-model="message" :placeholder="$t('campaigns.briefMessage')" :rows="3" class="mb-3 w-full" />
        <ul class="flex flex-col gap-2">
          <li
            v-for="c in available"
            :key="c.id"
            class="flex items-center justify-between rounded-lg border border-clay-200 p-3"
          >
            <span>{{ c.display_name }} <span class="text-sm text-ink-600">{{ c.city }}</span></span>
            <UButton
              size="sm"
              :disabled="!message.trim()"
              :loading="briefMutation.isPending.value"
              @click="briefMutation.mutate(c.id)"
            >
              {{ $t("campaigns.send") }}
            </UButton>
          </li>
        </ul>
      </template>
    </UCard>

    <section v-if="campaign.briefs.length" class="flex flex-col gap-2">
      <h2 class="text-lg font-semibold">{{ $t("campaigns.briefsList") }}</h2>
      <RouterLink
        v-for="b in campaign.briefs"
        :key="b.id"
        :to="`/briefs/${b.id}`"
        class="flex items-center justify-between rounded-xl bg-white p-4 shadow-sm hover:shadow"
      >
        <span>{{ b.creator_name }}</span>
        <UBadge :color="statusColor(b.status)" variant="subtle">{{ $t(`status.${b.status}`) }}</UBadge>
      </RouterLink>
    </section>

    <UAlert v-if="error" color="error" variant="subtle" :description="error" />
  </main>
</template>
