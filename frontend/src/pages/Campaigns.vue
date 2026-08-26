<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../lib/api";
import { kr } from "../lib/format";

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
const tiers = ref<Tier[]>([]);
const campaigns = ref<Campaign[]>([]);
const form = ref({ name: "", description: "", tier: "standard" });
const error = ref("");
const busy = ref(false);

onMounted(async () => {
  [tiers.value, campaigns.value] = await Promise.all([api<Tier[]>("/tiers"), api<Campaign[]>("/campaigns")]);
});

async function create() {
  error.value = "";
  busy.value = true;
  try {
    const campaign = await api<Campaign>("/campaigns", { method: "POST", body: JSON.stringify(form.value) });
    router.push(`/campaigns/${campaign.id}`);
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <main class="mx-auto flex max-w-2xl flex-col gap-8 px-4 py-8">
    <section class="rounded-2xl bg-white p-6 shadow">
      <h2 class="mb-4 text-lg font-semibold">{{ $t("campaigns.new") }}</h2>
      <form class="flex flex-col gap-3" @submit.prevent="create">
        <input v-model="form.name" :placeholder="$t('campaigns.name')" required class="input" />
        <textarea v-model="form.description" :placeholder="$t('campaigns.description')" rows="3" class="input" />
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
        <button :disabled="busy" class="rounded-lg bg-clay-600 py-3 font-medium text-white hover:bg-clay-700">
          {{ $t("campaigns.create") }}
        </button>
        <p v-if="error" class="text-sm text-red-700">{{ error }}</p>
      </form>
    </section>

    <section class="flex flex-col gap-3">
      <h1 class="text-xl font-semibold">{{ $t("campaigns.title") }}</h1>
      <p v-if="!campaigns.length" class="text-ink-600">{{ $t("campaigns.empty") }}</p>
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
          <span
            class="rounded-full px-3 py-1"
            :class="c.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-clay-100 text-ink-600'"
          >
            {{ $t(`status.${c.status}`) }}
          </span>
        </div>
      </RouterLink>
    </section>
  </main>
</template>

<style scoped>
@reference "../style.css";
.input {
  @apply rounded-lg border border-clay-200 bg-white px-4 py-3;
}
</style>
