<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { useRouter } from "vue-router";
import { api } from "../lib/api";
import { kr } from "../lib/format";

interface Tier {
  tier: string;
  price_ore: number;
  briefs: number;
}

const router = useRouter();
const { data: tiers } = useQuery({ queryKey: ["tiers"], queryFn: () => api<Tier[]>("/tiers"), staleTime: Infinity });

function signup() {
  sessionStorage.setItem("signup-intent", "brand");
  router.push("/auth");
}
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-10 px-6 py-14">
    <header class="flex flex-col items-center gap-4 text-center">
      <img src="/logo.png" alt="" class="h-20 w-20" />
      <h1 class="text-3xl font-semibold tracking-tight">{{ $t("forBrands.title") }}</h1>
      <p class="max-w-lg text-ink-600">{{ $t("forBrands.sub") }}</p>
    </header>

    <ol class="grid gap-4 sm:grid-cols-3">
      <li v-for="n in 3" :key="n" class="rounded-2xl bg-white p-5 shadow-sm">
        <span class="mb-2 flex h-8 w-8 items-center justify-center rounded-full bg-clay-100 font-semibold text-clay-700">
          {{ n }}
        </span>
        <h2 class="font-semibold">{{ $t(`forBrands.step${n}t`) }}</h2>
        <p class="mt-1 text-sm text-ink-600">{{ $t(`forBrands.step${n}d`) }}</p>
      </li>
    </ol>

    <section v-if="tiers" class="text-center">
      <h2 class="mb-4 text-lg font-semibold">{{ $t("forBrands.pricing") }}</h2>
      <div class="grid gap-3 sm:grid-cols-3">
        <div v-for="t in tiers" :key="t.tier" class="rounded-2xl border border-clay-200 bg-white p-5">
          <span class="block font-semibold capitalize">{{ t.tier }}</span>
          <span class="block text-2xl font-bold">{{ kr(t.price_ore) }}</span>
          <span class="block text-sm text-ink-600">{{ $t("campaigns.briefsIncluded", { count: t.briefs }) }}</span>
        </div>
      </div>
      <p class="mt-2 text-xs text-ink-600">{{ $t("forBrands.vat") }}</p>
    </section>

    <div class="flex flex-col items-center gap-3">
      <UButton size="xl" class="px-10" @click="signup">{{ $t("forBrands.cta") }}</UButton>
      <RouterLink to="/creators" class="text-sm text-ink-600 underline">{{ $t("forBrands.creatorInstead") }}</RouterLink>
    </div>
  </main>
</template>
