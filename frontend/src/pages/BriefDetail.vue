<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api } from "../lib/api";
import { kr } from "../lib/format";

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
const brief = ref<BriefDetail | null>(null);
const amountKr = ref<number | null>(null);
const proposalMessage = ref("");
const error = ref("");
const busy = ref(false);

async function load() {
  brief.value = await api<BriefDetail>(`/briefs/${id}`);
}
onMounted(load);

const openProposal = computed(() => brief.value?.proposals.find((p) => p.status === "open") ?? null);

async function act(fn: () => Promise<unknown>) {
  error.value = "";
  busy.value = true;
  try {
    await fn();
    await load();
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}

const propose = () =>
  act(() =>
    api(`/briefs/${id}/proposals`, {
      method: "POST",
      body: JSON.stringify({ amount_ore: Math.round((amountKr.value ?? 0) * 100), message: proposalMessage.value }),
    }),
  );
const accept = () => act(() => api(`/briefs/${id}/accept`, { method: "POST" }));
const decline = () => act(() => api(`/briefs/${id}/decline`, { method: "POST" }));
</script>

<template>
  <main v-if="brief" class="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
    <header class="rounded-2xl bg-white p-6 shadow">
      <div class="flex items-center justify-between">
        <h1 class="text-lg font-semibold">
          {{ brief.my_side === "brand" ? brief.creator_name : brief.brand_name }}
        </h1>
        <span class="rounded-full bg-clay-100 px-3 py-1 text-sm text-ink-600">{{ $t(`status.${brief.status}`) }}</span>
      </div>
      <p class="mt-1 text-sm text-ink-600">{{ brief.campaign_name }}</p>
      <p class="mt-3 whitespace-pre-wrap">{{ brief.message }}</p>
    </header>

    <section class="rounded-2xl bg-white p-6 shadow">
      <h2 class="mb-1 text-lg font-semibold">{{ $t("brief.negotiation") }}</h2>
      <p class="mb-4 text-sm text-ink-600">{{ $t("brief.youAre", { side: $t(`brief.${brief.my_side}`) }) }}</p>

      <ol class="flex flex-col gap-3">
        <li
          v-for="p in brief.proposals"
          :key="p.id"
          class="rounded-xl border p-4"
          :class="p.author === brief.my_side ? 'ml-8 border-clay-200 bg-clay-50' : 'mr-8 border-clay-200'"
        >
          <div class="flex items-center justify-between text-sm text-ink-600">
            <span>{{ $t("brief.round", { round: p.round }) }} · {{ $t(`brief.${p.author}`) }}</span>
            <span
              v-if="p.status !== 'open'"
              class="rounded-full px-2 py-0.5 text-xs"
              :class="p.status === 'accepted' ? 'bg-green-100 text-green-800' : 'bg-clay-100'"
            >
              {{ $t(`status.${p.status}`) ?? p.status }}
            </span>
          </div>
          <p class="mt-1 text-xl font-semibold">{{ kr(p.amount_ore) }}</p>
          <p v-if="p.message" class="mt-1 text-sm">{{ p.message }}</p>
        </li>
      </ol>

      <form v-if="brief.can_propose" class="mt-4 flex flex-col gap-3" @submit.prevent="propose">
        <input
          v-model.number="amountKr"
          type="number"
          min="1"
          step="1"
          required
          :placeholder="$t('brief.amountKr')"
          class="input"
        />
        <textarea v-model="proposalMessage" :placeholder="$t('brief.proposalMessage')" rows="2" class="input" />
        <button :disabled="busy" class="rounded-lg bg-clay-600 py-3 font-medium text-white hover:bg-clay-700">
          {{ $t("brief.submitProposal") }}
        </button>
      </form>

      <div class="mt-4 flex gap-3">
        <button
          v-if="brief.can_accept && openProposal"
          :disabled="busy"
          class="flex-1 rounded-lg bg-green-700 py-3 font-medium text-white hover:bg-green-800"
          @click="accept"
        >
          {{ $t("brief.accept", { amount: kr(openProposal.amount_ore) }) }}
        </button>
        <button
          v-if="brief.can_decline"
          :disabled="busy"
          class="rounded-lg border border-clay-200 px-6 py-3 text-ink-600 hover:border-red-300 hover:text-red-700"
          @click="decline"
        >
          {{ $t("brief.decline") }}
        </button>
      </div>

      <p
        v-if="!brief.can_propose && !brief.can_accept && ['sent', 'negotiating'].includes(brief.status)"
        class="mt-4 text-sm text-ink-600"
      >
        {{ $t("brief.waiting") }}
      </p>

      <RouterLink
        v-if="brief.deal_id"
        :to="`/deals/${brief.deal_id}`"
        class="mt-4 block rounded-lg bg-clay-600 py-3 text-center font-medium text-white hover:bg-clay-700"
      >
        {{ $t("brief.goToChat") }}
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
