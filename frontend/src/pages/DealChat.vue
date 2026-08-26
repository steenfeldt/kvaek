<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api } from "../lib/api";
import { kr } from "../lib/format";

interface Deal {
  id: number;
  campaign_name: string;
  counterpart_name: string;
  agreed_amount_ore: number;
  completed: boolean;
  completed_by_me: boolean;
  completed_by_other: boolean;
  reviewed_by_me: boolean;
}
interface Message {
  id: number;
  mine: boolean;
  body: string;
  created_at: string;
}

const route = useRoute();
const id = route.params.id as string;
const deal = ref<Deal | null>(null);
const messages = ref<Message[]>([]);
const draft = ref("");
const rating = ref(5);
const reviewText = ref("");
const reviewDone = ref(false);
const error = ref("");
const thread = ref<HTMLElement | null>(null);
let timer: ReturnType<typeof setInterval> | undefined;

async function scrollDown() {
  await nextTick();
  thread.value?.scrollTo({ top: thread.value.scrollHeight });
}

async function fetchMessages() {
  const lastId = messages.value.at(-1)?.id ?? 0;
  const fresh = await api<Message[]>(`/deals/${id}/messages?after_id=${lastId}`);
  if (fresh.length) {
    messages.value.push(...fresh);
    scrollDown();
  }
}

onMounted(async () => {
  deal.value = await api<Deal>(`/deals/${id}`);
  await fetchMessages();
  timer = setInterval(fetchMessages, 3000);
});
onUnmounted(() => clearInterval(timer));

async function send() {
  const body = draft.value.trim();
  if (!body) return;
  draft.value = "";
  const m = await api<Message>(`/deals/${id}/messages`, { method: "POST", body: JSON.stringify({ body }) });
  messages.value.push(m);
  scrollDown();
}

async function complete() {
  deal.value = await api<Deal>(`/deals/${id}/complete`, { method: "POST" });
}

async function submitReview() {
  error.value = "";
  try {
    await api(`/deals/${id}/reviews`, {
      method: "POST",
      body: JSON.stringify({ rating: rating.value, text: reviewText.value }),
    });
    reviewDone.value = true;
  } catch (e) {
    error.value = (e as Error).message;
  }
}
</script>

<template>
  <main v-if="deal" class="mx-auto flex h-[calc(100vh-3.5rem)] max-w-2xl flex-col px-4 py-4">
    <header class="rounded-2xl bg-white p-4 shadow">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="font-semibold">{{ deal.counterpart_name }}</h1>
          <p class="text-sm text-ink-600">
            {{ deal.campaign_name }} · {{ $t("deals.agreed", { amount: kr(deal.agreed_amount_ore) }) }}
          </p>
        </div>
        <button
          v-if="!deal.completed_by_me"
          class="rounded-lg border border-clay-200 px-3 py-2 text-sm hover:border-green-400"
          @click="complete"
        >
          {{ $t("chat.markComplete") }}
        </button>
      </div>
      <p v-if="deal.completed" class="mt-2 text-sm text-green-700">{{ $t("chat.completedBoth") }}</p>
      <template v-else>
        <p v-if="deal.completed_by_me" class="mt-2 text-sm text-ink-600">{{ $t("chat.completedByYou") }}</p>
        <p v-if="deal.completed_by_other" class="mt-1 text-sm text-ink-600">{{ $t("chat.completedByOther") }}</p>
      </template>
    </header>

    <div ref="thread" class="my-4 flex-1 space-y-2 overflow-y-auto">
      <div
        v-for="m in messages"
        :key="m.id"
        class="max-w-[80%] rounded-2xl px-4 py-2"
        :class="m.mine ? 'ml-auto bg-clay-600 text-white' : 'bg-white shadow-sm'"
      >
        <p class="whitespace-pre-wrap">{{ m.body }}</p>
      </div>
    </div>

    <section
      v-if="deal.completed && !deal.reviewed_by_me && !reviewDone"
      class="mb-3 rounded-2xl bg-white p-4 shadow"
    >
      <h2 class="mb-2 font-semibold">{{ $t("chat.review") }}</h2>
      <div class="mb-2 flex gap-1 text-2xl">
        <button v-for="n in 5" :key="n" @click="rating = n">{{ n <= rating ? "★" : "☆" }}</button>
      </div>
      <textarea v-model="reviewText" :placeholder="$t('chat.reviewText')" rows="2" class="input mb-2 w-full" />
      <button class="w-full rounded-lg bg-clay-600 py-2 text-white" @click="submitReview">
        {{ $t("chat.submitReview") }}
      </button>
      <p v-if="error" class="mt-2 text-sm text-red-700">{{ error }}</p>
    </section>
    <p v-else-if="reviewDone" class="mb-3 text-center text-sm text-green-700">{{ $t("chat.reviewed") }}</p>

    <form class="flex gap-2" @submit.prevent="send">
      <input v-model="draft" :placeholder="$t('chat.placeholder')" class="input flex-1" />
      <button class="rounded-lg bg-clay-600 px-6 py-3 font-medium text-white hover:bg-clay-700">
        {{ $t("chat.send") }}
      </button>
    </form>
  </main>
</template>

<style scoped>
@reference "../style.css";
.input {
  @apply rounded-lg border border-clay-200 bg-white px-4 py-3;
}
</style>
