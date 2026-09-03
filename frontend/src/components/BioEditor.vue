<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { api } from "../lib/api";
import { bioToDoc, docToBio, normalizeTag } from "../lib/hashtags";

// Plain-text bio with `#hashtags`. Tiptap (via UEditor) renders the tags as
// chips and offers suggestions after '#'; the model stays a plain string, so
// the API and every other reader see ordinary text.
const model = defineModel<string>({ default: "" });
const { t } = useI18n();

const doc = ref<object>(bioToDoc(model.value));
watch(model, (text) => {
  if (docToBio(doc.value as never) !== text) doc.value = bioToDoc(text);
});
function onUpdate(value: object) {
  doc.value = value;
  const text = docToBio(value as never);
  if (text !== model.value) model.value = text;
}

const searchTerm = ref("");
const { data: suggestions } = useQuery({
  queryKey: computed(() => ["hashtags", searchTerm.value]),
  queryFn: () => api<{ tag: string; count: number }[]>(`/hashtags?q=${encodeURIComponent(searchTerm.value)}`),
  placeholderData: (prev) => prev,
  staleTime: 60_000,
});

const items = computed(() => {
  const typed = normalizeTag(searchTerm.value);
  const known = (suggestions.value ?? []).map((s) => ({
    id: s.tag,
    label: s.tag,
    description: t("hashtags.creators", { count: s.count }, s.count),
  }));
  // Existing tags first so Enter picks the common spelling; the typed word
  // stays available as a new tag at the bottom.
  if (typed && !known.some((k) => k.id === typed)) {
    known.push({ id: typed, label: typed, description: t("hashtags.new") });
  }
  return known;
});
</script>

<template>
  <UEditor
    :model-value="doc"
    content-type="json"
    :starter-kit="false"
    :image="false"
    :placeholder="$t('hashtags.placeholder')"
    class="bio-editor w-full rounded-md bg-white text-sm ring ring-inset ring-clay-200 focus-within:ring-2 focus-within:ring-sage-500"
    @update:model-value="onUpdate"
  >
    <template #default="{ editor }">
      <UEditorMentionMenu
        v-if="editor"
        v-model:search-term="searchTerm"
        :editor="editor"
        char="#"
        :items="items"
        ignore-filter
      />
    </template>
  </UEditor>
</template>

<style scoped>
.bio-editor :deep(.ProseMirror) {
  min-height: 4.5rem;
  padding: 0.5rem 0.75rem;
  outline: none;
}
.bio-editor :deep(.mention) {
  color: var(--color-fjord-700);
  font-weight: 500;
}
</style>
