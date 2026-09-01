<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { nextTick, ref, watch } from "vue";
import { useRoute } from "vue-router";
import ReportButton from "../components/ReportButton.vue";
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
const queryClient = useQueryClient();
const toast = useToast();

const { data: deal } = useQuery({ queryKey: ["deal", id], queryFn: () => api<Deal>(`/deals/${id}`) });

// Polls while the tab is focused; Vue Query pauses refetching in background tabs.
const { data: messages } = useQuery({
  queryKey: ["messages", id],
  queryFn: () => api<Message[]>(`/deals/${id}/messages`),
  refetchInterval: 3000,
});

const thread = ref<HTMLElement | null>(null);
watch(
  () => messages.value?.length,
  async () => {
    await nextTick();
    thread.value?.scrollTo({ top: thread.value.scrollHeight });
  },
);

const draft = ref("");

const sendMutation = useMutation({
  mutationFn: (body: string) =>
    api<Message>(`/deals/${id}/messages`, { method: "POST", body: JSON.stringify({ body }) }),
  onSuccess: (m) => {
    queryClient.setQueryData<Message[]>(["messages", id], (old) => [...(old ?? []), m]);
  },
});

function send() {
  const body = draft.value.trim();
  if (!body) return;
  draft.value = "";
  sendMutation.mutate(body);
}

const completeMutation = useMutation({
  mutationFn: () => api<Deal>(`/deals/${id}/complete`, { method: "POST" }),
  onSuccess: (d) => {
    queryClient.setQueryData(["deal", id], d);
    queryClient.invalidateQueries({ queryKey: ["deals"] });
  },
});

const rating = ref(5);
const reviewText = ref("");
const reviewDone = ref(false);

const reviewMutation = useMutation({
  mutationFn: () =>
    api(`/deals/${id}/reviews`, {
      method: "POST",
      body: JSON.stringify({ rating: rating.value, text: reviewText.value }),
    }),
  onSuccess: () => (reviewDone.value = true),
  onError: (e) => toast.add({ title: e.message, color: "error" }),
});
</script>

<template>
  <main v-if="deal" class="mx-auto flex h-[calc(100vh-3.5rem)] max-w-2xl flex-col px-4 py-4">
    <UCard>
      <div class="flex items-center justify-between">
        <div>
          <h1 class="font-semibold">{{ deal.counterpart_name }}</h1>
          <p class="text-sm text-ink-600">
            {{ deal.campaign_name }} · {{ $t("deals.agreed", { amount: kr(deal.agreed_amount_ore) }) }}
          </p>
        </div>
        <div class="flex items-center gap-1">
          <ReportButton :deal-id="deal.id" />
          <UButton
            v-if="!deal.completed_by_me"
            variant="outline"
            color="neutral"
            size="sm"
            :loading="completeMutation.isPending.value"
            @click="completeMutation.mutate()"
          >
            {{ $t("chat.markComplete") }}
          </UButton>
        </div>
      </div>
      <p v-if="deal.completed" class="mt-2 text-sm text-green-700">{{ $t("chat.completedBoth") }}</p>
      <template v-else>
        <p v-if="deal.completed_by_me" class="mt-2 text-sm text-ink-600">{{ $t("chat.completedByYou") }}</p>
        <p v-if="deal.completed_by_other" class="mt-1 text-sm text-ink-600">{{ $t("chat.completedByOther") }}</p>
      </template>
    </UCard>

    <div ref="thread" class="my-4 flex-1 space-y-2 overflow-y-auto">
      <div
        v-for="m in messages"
        :key="m.id"
        class="max-w-[80%] rounded-2xl px-4 py-2"
        :class="m.mine ? 'ml-auto bg-sage-600 text-white' : 'bg-white shadow-sm'"
      >
        <p class="whitespace-pre-wrap">{{ m.body }}</p>
      </div>
    </div>

    <UCard v-if="deal.completed && !deal.reviewed_by_me && !reviewDone" class="mb-3">
      <h2 class="mb-2 font-semibold">{{ $t("chat.review") }}</h2>
      <div class="mb-2 flex gap-1 text-2xl">
        <button v-for="n in 5" :key="n" type="button" @click="rating = n">{{ n <= rating ? "★" : "☆" }}</button>
      </div>
      <UTextarea v-model="reviewText" :placeholder="$t('chat.reviewText')" :rows="2" class="mb-2 w-full" />
      <UButton block :loading="reviewMutation.isPending.value" @click="reviewMutation.mutate()">
        {{ $t("chat.submitReview") }}
      </UButton>
    </UCard>
    <p v-else-if="reviewDone" class="mb-3 text-center text-sm text-green-700">{{ $t("chat.reviewed") }}</p>

    <form class="flex gap-2" @submit.prevent="send">
      <UInput v-model="draft" :placeholder="$t('chat.placeholder')" size="lg" class="flex-1" />
      <UButton type="submit" size="lg">{{ $t("chat.send") }}</UButton>
    </form>
  </main>
</template>
