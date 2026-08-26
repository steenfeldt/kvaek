<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { api } from "../lib/api";

interface Niche {
  name: string;
  slug: string;
}

const model = defineModel<string[]>({ required: true });

const { data: niches } = useQuery({
  queryKey: ["niches"],
  queryFn: () => api<Niche[]>("/niches"),
  staleTime: Infinity,
});

function toggle(slug: string) {
  model.value = model.value.includes(slug)
    ? model.value.filter((s) => s !== slug)
    : [...model.value, slug];
}
</script>

<template>
  <div class="flex flex-wrap gap-2">
    <button
      v-for="n in niches"
      :key="n.slug"
      type="button"
      class="rounded-full border px-3 py-1 text-sm transition"
      :class="
        model.includes(n.slug)
          ? 'border-clay-600 bg-clay-600 text-white'
          : 'border-clay-200 bg-white text-ink-600 hover:border-clay-500'
      "
      @click="toggle(n.slug)"
    >
      {{ n.name }}
    </button>
  </div>
</template>
