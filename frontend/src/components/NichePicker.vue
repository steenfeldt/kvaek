<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { ref } from "vue";
import { api } from "../lib/api";

interface Niche {
  name: string;
  slug: string;
  // The caller's own suggestion, awaiting staff approval (hidden from others).
  pending?: boolean;
}

const model = defineModel<string[]>({ required: true });
const queryClient = useQueryClient();

const { data: niches } = useQuery({
  queryKey: ["niches"],
  queryFn: () => api<Niche[]>("/niches"),
  staleTime: 5 * 60 * 1000,
});

function toggle(slug: string) {
  model.value = model.value.includes(slug) ? model.value.filter((s) => s !== slug) : [...model.value, slug];
}

const suggesting = ref(false);
const suggestion = ref("");
const suggestError = ref("");

const suggestMutation = useMutation({
  mutationFn: () => api<Niche>("/niches/suggest", { method: "POST", body: JSON.stringify({ name: suggestion.value }) }),
  onSuccess: (niche) => {
    queryClient.setQueryData<Niche[]>(["niches"], (list = []) =>
      list.some((n) => n.slug === niche.slug) ? list : [...list, niche].sort((a, b) => a.name.localeCompare(b.name, "da")),
    );
    if (!model.value.includes(niche.slug)) model.value = [...model.value, niche.slug];
    suggestion.value = "";
    suggestError.value = "";
    suggesting.value = false;
  },
  onError: (e) => (suggestError.value = (e as Error).message),
});
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex flex-wrap gap-2">
      <button
        v-for="n in niches"
        :key="n.slug"
        type="button"
        class="flex items-center gap-1 rounded-full border px-3 py-1 text-sm transition"
        :class="[
          model.includes(n.slug)
            ? 'border-sage-600 bg-sage-600 text-white'
            : 'border-clay-200 bg-white text-ink-600 hover:border-sage-500',
          n.pending && 'border-dashed',
        ]"
        :title="n.pending ? $t('niches.pending') : undefined"
        @click="toggle(n.slug)"
      >
        <UIcon v-if="n.pending" name="i-lucide-clock" class="size-3.5" />
        {{ n.name }}
      </button>
      <button
        v-if="!suggesting"
        type="button"
        class="flex items-center gap-1 rounded-full border border-dashed border-clay-300 bg-white px-3 py-1 text-sm text-ink-600 hover:border-sage-500"
        @click="suggesting = true"
      >
        <UIcon name="i-lucide-plus" class="size-3.5" />
        {{ $t("niches.suggest") }}
      </button>
    </div>
    <!-- Not a <form>: the picker sits inside the profile/onboarding form. -->
    <div v-if="suggesting" class="flex flex-col gap-2">
      <div class="flex gap-2">
        <UInput
          v-model="suggestion"
          :placeholder="$t('niches.suggestPlaceholder')"
          maxlength="50"
          autofocus
          class="flex-1"
          @keydown.enter.prevent="suggestion.trim().length >= 2 && suggestMutation.mutate()"
        />
        <UButton
          type="button"
          :loading="suggestMutation.isPending.value"
          :disabled="suggestion.trim().length < 2"
          @click="suggestMutation.mutate()"
        >
          {{ $t("niches.send") }}
        </UButton>
        <UButton type="button" variant="ghost" color="neutral" @click="suggesting = false">{{ $t("portfolio.cancel") }}</UButton>
      </div>
      <p class="text-xs text-ink-600">{{ $t("niches.suggestHint") }}</p>
      <p v-if="suggestError" class="text-xs text-red-700">{{ suggestError }}</p>
    </div>
  </div>
</template>
