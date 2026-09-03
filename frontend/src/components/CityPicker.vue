<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { refDebounced } from "@vueuse/core";
import { computed, ref } from "vue";
import { searchCities, type CityOption } from "../lib/cities";

// Searchable dropdown over the City table (Danish towns synced from DAWA).
const model = defineModel<CityOption | null>({ default: null });
const search = ref("");
const term = refDebounced(search, 200);

const { data, isFetching } = useQuery({
  queryKey: computed(() => ["cities", term.value]),
  queryFn: () => searchCities(term.value),
  enabled: computed(() => term.value.trim().length > 0),
  placeholderData: (prev) => prev,
  staleTime: 5 * 60 * 1000,
});
const items = computed(() => (term.value.trim() ? (data.value ?? []) : []));
</script>

<template>
  <div class="flex gap-2">
    <UInputMenu
      v-model="model"
      v-model:search-term="search"
      :items="items"
      ignore-filter
      :loading="isFetching"
      :placeholder="$t('city.search')"
      class="flex-1"
    >
      <template #empty>
        {{ search.trim() ? $t("city.none") : $t("city.typeToSearch") }}
      </template>
    </UInputMenu>
    <UButton
      v-if="model"
      icon="i-lucide-x"
      variant="ghost"
      color="neutral"
      :aria-label="$t('city.clear')"
      @click="model = null"
    />
  </div>
</template>
