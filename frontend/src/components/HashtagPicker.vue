<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { refDebounced } from "@vueuse/core";
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { api } from "../lib/api";
import { normalizeTag } from "../lib/hashtags";

// Pick one hashtag (bare, without '#') from those in use by listed creators.
const model = defineModel<string>({ default: "" });
const { t } = useI18n();
const search = ref("");
const term = refDebounced(search, 150);

const { data, isFetching } = useQuery({
  queryKey: computed(() => ["hashtags", normalizeTag(term.value)]),
  queryFn: () => api<{ tag: string; count: number }[]>(`/hashtags?q=${encodeURIComponent(normalizeTag(term.value))}`),
  placeholderData: (prev) => prev,
  staleTime: 60_000,
});
const items = computed(() =>
  (data.value ?? []).map((s) => ({
    label: `#${s.tag}`,
    value: s.tag,
    description: t("hashtags.creators", { count: s.count }, s.count),
  })),
);
</script>

<template>
  <div class="flex gap-2">
    <UInputMenu
      v-model="model"
      v-model:search-term="search"
      :items="items"
      value-key="value"
      ignore-filter
      :loading="isFetching"
      icon="i-lucide-hash"
      :placeholder="$t('deck.filterPlaceholder')"
      class="flex-1"
    >
      <template #empty>{{ $t("deck.noTags") }}</template>
    </UInputMenu>
    <UButton
      v-if="model"
      icon="i-lucide-x"
      variant="ghost"
      color="neutral"
      :aria-label="$t('deck.clearFilter')"
      @click="model = ''"
    />
  </div>
</template>
