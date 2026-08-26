<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "../lib/api";

interface Social {
  platform: string;
  follower_count: number;
  verified: boolean;
}
interface Card {
  id: number;
  display_name: string;
  city: string;
  bio: string;
  niches: string[];
  verified: boolean;
  photos: string[];
  socials: Social[];
}

const cards = ref<Card[]>([]);
const loading = ref(true);

async function load() {
  loading.value = true;
  cards.value = await api<Card[]>("/deck");
  loading.value = false;
}

async function swipe(direction: "like" | "pass") {
  const card = cards.value[0];
  if (!card) return;
  cards.value = cards.value.slice(1);
  await api("/swipes", { method: "POST", body: JSON.stringify({ creator_id: card.id, direction }) });
  if (cards.value.length === 0) await load();
}

onMounted(load);
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 px-6 py-10">
    <div v-if="cards[0]" class="overflow-hidden rounded-2xl bg-white shadow-lg">
      <img
        v-if="cards[0].photos[0]"
        :src="cards[0].photos[0]"
        class="aspect-square w-full object-cover"
        alt=""
      />
      <div v-else class="flex aspect-square w-full items-center justify-center bg-clay-100 text-6xl">📷</div>
      <div class="flex flex-col gap-2 p-5">
        <h2 class="text-xl font-semibold">
          {{ cards[0].display_name }}
          <span v-if="cards[0].verified" title="Verified">✔</span>
          <span class="ml-2 text-sm font-normal text-ink-600">{{ cards[0].city }}</span>
        </h2>
        <p class="text-sm text-ink-600">{{ cards[0].bio }}</p>
        <div class="flex flex-wrap gap-2 text-xs">
          <span v-for="n in cards[0].niches" :key="n" class="rounded-full bg-clay-100 px-3 py-1">{{ n }}</span>
        </div>
        <div class="flex gap-4 text-sm text-ink-600">
          <span v-for="s in cards[0].socials" :key="s.platform">
            {{ s.platform }}: {{ s.follower_count.toLocaleString("da-DK") }} {{ $t("deck.followers") }}
          </span>
        </div>
      </div>
    </div>
    <p v-else-if="!loading" class="text-center text-ink-600">{{ $t("deck.empty") }}</p>

    <div v-if="cards[0]" class="flex justify-center gap-4">
      <button class="rounded-full border-2 border-clay-200 bg-white px-8 py-3 font-medium" @click="swipe('pass')">
        {{ $t("deck.pass") }}
      </button>
      <button class="rounded-full bg-clay-600 px-8 py-3 font-medium text-white hover:bg-clay-700" @click="swipe('like')">
        {{ $t("deck.like") }}
      </button>
    </div>
  </main>
</template>
