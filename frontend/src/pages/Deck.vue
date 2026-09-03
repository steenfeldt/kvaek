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
        <img v-if="top.photos[0]" :src="top.photos[0]" class="aspect-square w-full object-cover" alt="" draggable="false" />
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
