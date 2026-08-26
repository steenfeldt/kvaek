<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api } from "../lib/api";

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
const campaign = ref<Campaign | null>(null);
const shortlisted = ref<Card[]>([]);
const message = ref("");
const sentTo = ref(new Set<number>());
const error = ref("");
const busy = ref(false);

async function load() {
  campaign.value = await api<Campaign>(`/campaigns/${id}`);
  const lists = await api<Shortlist[]>("/shortlists");
  const cards = await Promise.all(lists.map((l) => api<Card[]>(`/shortlists/${l.id}`)));
  const briefed = new Set(campaign.value.briefs.map((b) => b.creator_id));
  const seen = new Set<number>();
  shortlisted.value = cards.flat().filter((c) => {
    if (seen.has(c.id) || briefed.has(c.id)) return false;
    seen.add(c.id);
    return true;
  });
}
onMounted(load);

const quotaLeft = computed(() =>
  campaign.value ? campaign.value.briefs_total - campaign.value.briefs_used : 0,
);

async function pay() {
  busy.value = true;
  error.value = "";
  try {
    const res = await api<{ checkout_url: string; campaign_status: string }>(
      `/campaigns/${id}/checkout`,
      { method: "POST" },
    );
    if (res.checkout_url) window.location.href = res.checkout_url;
    else await load();
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}

async function sendBrief(creatorId: number) {
  error.value = "";
  try {
    await api(`/campaigns/${id}/briefs`, {
      method: "POST",
      body: JSON.stringify({ creator_id: creatorId, message: message.value }),
    });
    sentTo.value.add(creatorId);
    await load();
  } catch (e) {
    error.value = (e as Error).message;
  }
}
</script>

<template>
  <main v-if="campaign" class="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
    <header class="rounded-2xl bg-white p-6 shadow">
      <div class="flex items-center justify-between">
        <h1 class="text-xl font-semibold">{{ campaign.name }}</h1>
        <span
          class="rounded-full px-3 py-1 text-sm"
          :class="campaign.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-clay-100 text-ink-600'"
        >
          {{ $t(`status.${campaign.status}`) }}
        </span>
      </div>
      <p class="mt-2 text-ink-600">{{ campaign.description }}</p>
      <p v-if="campaign.status === 'active'" class="mt-2 text-sm text-ink-600">
        {{ $t("campaigns.briefsUsed", { used: campaign.briefs_used, total: campaign.briefs_total }) }}
      </p>
      <button
        v-if="campaign.status === 'draft'"
        :disabled="busy"
        class="mt-4 w-full rounded-lg bg-clay-600 py-3 font-medium text-white hover:bg-clay-700"
        @click="pay"
      >
        {{ $t("campaigns.payActivate") }}
      </button>
    </header>

    <section v-if="campaign.status === 'active' && quotaLeft > 0" class="rounded-2xl bg-white p-6 shadow">
      <h2 class="mb-3 text-lg font-semibold">{{ $t("campaigns.sendBriefs") }}</h2>
      <p v-if="!shortlisted.length" class="text-ink-600">{{ $t("campaigns.noShortlisted") }}</p>
      <template v-else>
        <textarea v-model="message" :placeholder="$t('campaigns.briefMessage')" rows="3" class="input mb-3 w-full" />
        <ul class="flex flex-col gap-2">
          <li v-for="c in shortlisted" :key="c.id" class="flex items-center justify-between rounded-lg border border-clay-200 p-3">
            <span>{{ c.display_name }} <span class="text-sm text-ink-600">{{ c.city }}</span></span>
            <button
              v-if="!sentTo.has(c.id)"
              :disabled="!message.trim()"
              class="rounded-lg bg-clay-600 px-4 py-2 text-sm text-white disabled:opacity-40"
              @click="sendBrief(c.id)"
            >
              {{ $t("campaigns.send") }}
            </button>
            <span v-else class="text-sm text-green-700">{{ $t("campaigns.briefSent") }}</span>
          </li>
        </ul>
      </template>
    </section>

    <section v-if="campaign.briefs.length" class="flex flex-col gap-2">
      <h2 class="text-lg font-semibold">{{ $t("campaigns.briefsList") }}</h2>
      <RouterLink
        v-for="b in campaign.briefs"
        :key="b.id"
        :to="`/briefs/${b.id}`"
        class="flex items-center justify-between rounded-xl bg-white p-4 shadow-sm hover:shadow"
      >
        <span>{{ b.creator_name }}</span>
        <span class="rounded-full bg-clay-100 px-3 py-1 text-sm text-ink-600">{{ $t(`status.${b.status}`) }}</span>
      </RouterLink>
    </section>

    <p v-if="error" class="text-sm text-red-700">{{ error }}</p>
  </main>
</template>

<style scoped>
@reference "../style.css";
.input {
  @apply rounded-lg border border-clay-200 bg-white px-4 py-3;
}
</style>
