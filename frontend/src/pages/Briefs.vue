<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "../lib/api";
import { useSession } from "../stores/session";

interface Brief {
  id: number;
  creator_name: string;
  campaign_name: string;
  brand_name: string;
  message: string;
  status: string;
}

const session = useSession();
const briefs = ref<Brief[]>([]);

onMounted(async () => {
  briefs.value = await api<Brief[]>("/briefs");
});
</script>

<template>
  <main class="mx-auto flex max-w-2xl flex-col gap-3 px-4 py-8">
    <h1 class="text-xl font-semibold">{{ $t("briefs.title") }}</h1>
    <p v-if="!briefs.length" class="text-ink-600">{{ $t("briefs.empty") }}</p>
    <RouterLink
      v-for="b in briefs"
      :key="b.id"
      :to="`/briefs/${b.id}`"
      class="rounded-xl bg-white p-4 shadow-sm hover:shadow"
    >
      <div class="flex items-center justify-between">
        <span class="font-medium">
          {{ session.role === "brand" ? $t("briefs.to", { name: b.creator_name }) : $t("briefs.from", { name: b.brand_name }) }}
        </span>
        <span class="rounded-full bg-clay-100 px-3 py-1 text-sm text-ink-600">{{ $t(`status.${b.status}`) }}</span>
      </div>
      <p class="mt-1 text-sm text-ink-600">{{ b.campaign_name }}</p>
      <p class="mt-1 truncate text-sm">{{ b.message }}</p>
    </RouterLink>
  </main>
</template>
