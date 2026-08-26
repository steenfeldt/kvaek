<script setup lang="ts">
import { useMutation, useQuery } from "@tanstack/vue-query";
import { ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../lib/api";
import { kr } from "../lib/format";
import { statusColor } from "../lib/status";

interface Tier {
  tier: string;
  price_ore: number;
  briefs: number;
}
interface Campaign {
  id: number;
  name: string;
  description: string;
  tier: string;
  status: string;
  briefs_total: number;
  briefs_used: number;
}

const router = useRouter();
const { data: tiers } = useQuery({ queryKey: ["tiers"], queryFn: () => api<Tier[]>("/tiers"), staleTime: Infinity });
const { data: campaigns } = useQuery({ queryKey: ["campaigns"], queryFn: () => api<Campaign[]>("/campaigns") });

const form = ref({ name: "", description: "", tier: "standard" });

const createMutation = useMutation({
  mutationFn: () => api<Campaign>("/campaigns", { method: "POST", body: JSON.stringify(form.value) }),
  onSuccess: (campaign) => router.push(`/campaigns/${campaign.id}`),
});
</script>

<template>
  <main class="mx-auto flex max-w-2xl flex-col gap-8 px-4 py-8">
    <UCard>
      <h2 class="mb-4 text-lg font-semibold">{{ $t("campaigns.new") }}</h2>
      <form class="flex flex-col gap-4" @submit.prevent="createMutation.mutate()">
        <UFormField :label="$t('campaigns.name')" required>
          <UInput v-model="form.name" required class="w-full" />
        </UFormField>
        <UFormField :label="$t('campaigns.description')">
          <UTextarea v-model="form.description" :rows="3" class="w-full" />
        </UFormField>
        <div class="grid gap-3 sm:grid-cols-3">
          <label
            v-for="t in tiers"
            :key="t.tier"
            class="cursor-pointer rounded-xl border-2 p-4 text-center"
            :class="form.tier === t.tier ? 'border-clay-600 bg-clay-50' : 'border-clay-200'"
          >
            <input v-model="form.tier" type="radio" :value="t.tier" class="hidden" />
            <span class="block font-semibold capitalize">{{ t.tier }}</span>
            <span class="block text-2xl font-bold">{{ kr(t.price_ore) }}</span>
            <span class="block text-sm text-ink-600">{{ $t("campaigns.briefsIncluded", { count: t.briefs }) }}</span>
          </label>
        </div>
        <p class="text-xs text-ink-600">{{ $t("campaigns.vatNote") }}</p>
        <UButton type="submit" :loading="createMutation.isPending.value" size="lg" block>
          {{ $t("campaigns.create") }}
        </UButton>
        <UAlert
          v-if="createMutation.error.value"
          color="error"
          variant="subtle"
          :description="createMutation.error.value.message"
        />
      </form>
    </UCard>

    <section class="flex flex-col gap-3">
      <h1 class="text-xl font-semibold">{{ $t("campaigns.title") }}</h1>
      <p v-if="campaigns && !campaigns.length" class="text-ink-600">{{ $t("campaigns.empty") }}</p>
      <RouterLink
        v-for="c in campaigns"
        :key="c.id"
        :to="`/campaigns/${c.id}`"
        class="flex items-center justify-between rounded-xl bg-white p-4 shadow-sm hover:shadow"
      >
        <div>
          <span class="font-medium">{{ c.name }}</span>
          <span class="ml-2 text-sm text-ink-600 capitalize">{{ c.tier }}</span>
        </div>
        <div class="flex items-center gap-3 text-sm">
          <span v-if="c.status === 'active'" class="text-ink-600">
            {{ $t("campaigns.briefsUsed", { used: c.briefs_used, total: c.briefs_total }) }}
          </span>
          <UBadge :color="statusColor(c.status)" variant="subtle">{{ $t(`status.${c.status}`) }}</UBadge>
        </div>
      </RouterLink>
    </section>
  </main>
</template>
