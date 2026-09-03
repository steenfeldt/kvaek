<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { computed, ref, watch } from "vue";
import HashtagPicker from "../components/HashtagPicker.vue";
import HashtagText from "../components/HashtagText.vue";
import ReportButton from "../components/ReportButton.vue";
import { api } from "../lib/api";
import { platformInfo } from "../lib/platforms";

interface Social {
  platform: string;
  follower_count: number;
  verified: boolean;
}
interface PortfolioItem {
  id: number;
  media_type: "image" | "video";
  url: string;
  title: string;
  description: string;
}
interface Card {
  id: number;
  display_name: string;
  city: string;
  bio: string;
  niches: string[];
  verified: boolean;
  photo: string | null;
  portfolio: PortfolioItem[];
  socials: Social[];
}

// Portfolio item opened in a modal from the card's thumbnail strip.
const openItem = ref<PortfolioItem | null>(null);

const queryClient = useQueryClient();
// Optional hashtag filter (bare tag, no '#'); each tag has its own deck.
const tag = ref("");
const { data, isFetching } = useQuery({
  queryKey: computed(() => ["deck", tag.value]),
  queryFn: () => api<Card[]>(tag.value ? `/deck?tag=${encodeURIComponent(tag.value)}` : "/deck"),
  staleTime: 60_000,
});

// Cards swiped locally this round; cleared when the deck is refetched.
const removed = ref(new Set<number>());
watch(tag, () => (removed.value = new Set()));
const stack = computed(() => (data.value ?? []).filter((c) => !removed.value.has(c.id)));
const top = computed(() => stack.value[0] ?? null);

const swipeMutation = useMutation({
  mutationFn: (p: { creator_id: number; direction: string }) =>
    api("/swipes", { method: "POST", body: JSON.stringify(p) }),
});

// --- drag gesture on the top card ---
const dx = ref(0);
const dy = ref(0);
const dragging = ref(false);
const leaving = ref<null | "like" | "pass">(null);
let startX = 0;
let startY = 0;

const cardStyle = computed(() => {
  if (leaving.value) {
    const sign = leaving.value === "like" ? 1 : -1;
    return {
      transform: `translate(${sign * 600}px, ${dy.value}px) rotate(${sign * 30}deg)`,
      transition: "transform 0.3s ease-in",
      opacity: "0",
    };
  }
  if (dragging.value) {
    return { transform: `translate(${dx.value}px, ${dy.value}px) rotate(${dx.value * 0.05}deg)` };
  }
  return { transform: "translate(0,0)", transition: "transform 0.25s ease-out" };
});

function onPointerDown(e: PointerEvent) {
  if (leaving.value) return;
  dragging.value = true;
  startX = e.clientX;
  startY = e.clientY;
  (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
}

function onPointerMove(e: PointerEvent) {
  if (!dragging.value) return;
  dx.value = e.clientX - startX;
  dy.value = e.clientY - startY;
}

function onPointerUp() {
  if (!dragging.value) return;
  dragging.value = false;
  if (dx.value > 120) swipe("like");
  else if (dx.value < -120) swipe("pass");
  else {
    dx.value = 0;
    dy.value = 0;
  }
}

function swipe(direction: "like" | "pass") {
  const card = top.value;
  if (!card || leaving.value) return;
  leaving.value = direction;
  swipeMutation.mutate({ creator_id: card.id, direction });
  setTimeout(() => {
    removed.value.add(card.id);
    removed.value = new Set(removed.value);
    leaving.value = null;
    dx.value = 0;
    dy.value = 0;
    if (stack.value.length === 0) {
      removed.value = new Set();
      queryClient.invalidateQueries({ queryKey: ["deck"] });
    }
  }, 250);
}
</script>

<template>
  <main class="mx-auto flex max-w-md flex-col gap-6 px-6 py-8">
    <HashtagPicker v-model="tag" />
    <div class="relative" style="min-height: 480px">
      <!-- next card peeks behind -->
      <div
        v-if="stack[1]"
        class="absolute inset-0 scale-95 overflow-hidden rounded-2xl bg-white opacity-60 shadow"
      />
      <div
        v-if="top"
        class="relative touch-none overflow-hidden rounded-2xl bg-white shadow-lg select-none"
        :style="cardStyle"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="onPointerUp"
      >
        <img v-if="top.photo" :src="top.photo" class="aspect-square w-full object-cover" alt="" draggable="false" />
        <div v-else class="flex aspect-square w-full items-center justify-center bg-clay-100 text-6xl">📷</div>
        <div class="flex flex-col gap-2 p-5">
          <h2 class="flex items-center gap-1 text-xl font-semibold">
            {{ top.display_name }}
            <UBadge v-if="top.verified" color="success" variant="subtle" size="sm">✔</UBadge>
            <span class="ml-1 text-sm font-normal text-ink-600">{{ top.city }}</span>
            <span class="flex-1" />
            <ReportButton :creator-id="top.id" />
          </h2>
          <p class="text-sm text-ink-600"><HashtagText :text="top.bio" /></p>
          <div class="flex flex-wrap gap-2">
            <UBadge v-for="n in top.niches" :key="n" color="primary" variant="subtle" size="sm">{{ n }}</UBadge>
          </div>
          <div v-if="top.portfolio.length" class="flex gap-2 overflow-x-auto py-1">
            <button
              v-for="item in top.portfolio"
              :key="item.id"
              type="button"
              class="relative h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-clay-100"
              :title="item.title"
              @pointerdown.stop
              @click.stop="openItem = item"
            >
              <video v-if="item.media_type === 'video'" :src="item.url" class="h-full w-full object-cover" muted preload="metadata" />
              <img v-else :src="item.url" class="h-full w-full object-cover" alt="" draggable="false" />
              <UIcon v-if="item.media_type === 'video'" name="i-lucide-play" class="absolute inset-0 m-auto size-6 text-white drop-shadow" />
            </button>
          </div>
          <div class="flex gap-4 text-sm text-ink-600">
            <span v-for="s in top.socials" :key="s.platform" class="flex items-center gap-1">
              <UIcon :name="platformInfo(s.platform).icon" class="size-4" :title="platformInfo(s.platform).label" />
              {{ s.follower_count.toLocaleString("da-DK") }}
              <span class="sr-only">{{ platformInfo(s.platform).label }} {{ $t("deck.followers") }}</span>
            </span>
          </div>
        </div>
        <!-- drag feedback -->
        <div
          v-if="dx > 40"
          class="absolute top-6 left-6 rotate-[-15deg] rounded-lg border-4 border-green-600 px-3 py-1 text-2xl font-bold text-green-600"
        >
          {{ $t("deck.like") }}
        </div>
        <div
          v-if="dx < -40"
          class="absolute top-6 right-6 rotate-[15deg] rounded-lg border-4 border-red-500 px-3 py-1 text-2xl font-bold text-red-500"
        >
          {{ $t("deck.pass") }}
        </div>
      </div>
      <div v-else-if="!isFetching" class="flex h-full min-h-[480px] items-center justify-center">
        <p class="text-center text-ink-600">{{ tag ? $t("deck.emptyTag", { tag }) : $t("deck.empty") }}</p>
      </div>
    </div>

    <UModal :open="!!openItem" :title="openItem?.title" @update:open="(v) => !v && (openItem = null)">
      <template #body>
        <template v-if="openItem">
          <video v-if="openItem.media_type === 'video'" :src="openItem.url" class="w-full rounded-lg bg-black" controls autoplay playsinline />
          <img v-else :src="openItem.url" class="w-full rounded-lg" alt="" />
          <p v-if="openItem.description" class="mt-3 text-sm whitespace-pre-line text-ink-600">{{ openItem.description }}</p>
        </template>
      </template>
    </UModal>

    <div v-if="top" class="flex justify-center gap-4">
      <UButton variant="outline" color="neutral" size="xl" class="rounded-full px-8" @click="swipe('pass')">
        {{ $t("deck.pass") }}
      </UButton>
      <UButton size="xl" class="rounded-full px-8" @click="swipe('like')">
        {{ $t("deck.like") }}
      </UButton>
    </div>
  </main>
</template>
