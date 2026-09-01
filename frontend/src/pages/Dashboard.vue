<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { ref } from "vue";
import KvaekkerGame from "../components/KvaekkerGame.vue";
import { api } from "../lib/api";
import { useGreeting } from "../lib/greeting";

interface PoolCreator {
  id: number;
  display_name: string;
  city: string;
  photo: string | null;
}

interface Dashboard {
  company_name: string;
  city: string;
  waiting_proposals: number;
  active_campaigns: number;
  deals_in_flight: number;
  pool_total: number;
  pool_in_city: number;
  new_in_pool: PoolCreator[];
}

const { data } = useQuery({
  queryKey: ["brand-dashboard"],
  queryFn: () => api<Dashboard>("/dashboard/brand"),
});
const { today, greeting } = useGreeting();
const gameOpen = ref(false);
</script>

<template>
  <main class="mx-auto flex max-w-3xl flex-col gap-10 px-6 pt-12 pb-16">
    <header v-if="data">
      <p class="text-xs font-semibold uppercase tracking-widest text-clay-600">
        <span aria-hidden="true">●</span> {{ $t("dashboard.yourWeek") }} · {{ today }}
      </p>
      <h1 class="mt-2 text-3xl font-semibold sm:text-4xl">
        {{ greeting }}, <span class="text-clay-700">{{ data.company_name }}</span
        >.
      </h1>
      <p v-if="data.city" class="mt-1 text-sm text-ink-600">{{ data.city }}</p>
    </header>

    <section
      v-if="data"
      class="grid grid-cols-1 divide-y divide-clay-200 border-y border-clay-200 sm:grid-cols-3 sm:divide-x sm:divide-y-0"
    >
      <RouterLink to="/briefs" class="px-5 py-6 transition-colors hover:bg-clay-50">
        <p class="text-xs font-semibold uppercase tracking-widest text-ink-600">
          {{ $t("dashboard.waitingOnYou") }}
        </p>
        <p class="mt-2 text-4xl font-semibold text-clay-600">{{ data.waiting_proposals }}</p>
        <p class="mt-1 text-sm text-ink-600">{{ $t("dashboard.waitingSub") }}</p>
      </RouterLink>
      <RouterLink to="/campaigns" class="px-5 py-6 transition-colors hover:bg-clay-50">
        <p class="text-xs font-semibold uppercase tracking-widest text-ink-600">
          {{ $t("dashboard.activeCampaigns") }}
        </p>
        <p class="mt-2 text-4xl font-semibold text-fjord-600">{{ data.active_campaigns }}</p>
        <p class="mt-1 text-sm text-ink-600">{{ $t("dashboard.activeSub") }}</p>
      </RouterLink>
      <RouterLink to="/deals" class="px-5 py-6 transition-colors hover:bg-clay-50">
        <p class="text-xs font-semibold uppercase tracking-widest text-ink-600">
          {{ $t("dashboard.dealsInFlight") }}
        </p>
        <p class="mt-2 text-4xl font-semibold text-sage-600">{{ data.deals_in_flight }}</p>
        <p class="mt-1 text-sm text-ink-600">{{ $t("dashboard.dealsSub") }}</p>
      </RouterLink>
    </section>

    <section v-if="data && data.new_in_pool.length">
      <div class="flex flex-wrap items-baseline justify-between gap-2">
        <h2 class="text-xl font-semibold">{{ $t("dashboard.newInPool") }}</h2>
        <p class="text-sm text-ink-600">
          {{ $t("dashboard.poolTotal", { total: data.pool_total }) }}
          <template v-if="data.city && data.pool_in_city">
            · {{ $t("dashboard.poolInCity", { count: data.pool_in_city, city: data.city }) }}
          </template>
        </p>
      </div>
      <div class="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <RouterLink v-for="c in data.new_in_pool" :key="c.id" to="/deck" class="group">
          <img
            v-if="c.photo"
            :src="c.photo"
            alt=""
            class="aspect-[3/4] w-full rounded-xl bg-clay-100 object-cover transition-transform group-hover:scale-[1.02]"
          />
          <div
            v-else
            class="flex aspect-[3/4] w-full items-center justify-center rounded-xl bg-clay-100 text-4xl"
          >
            🐸
          </div>
          <p class="mt-2 text-sm font-medium">{{ c.display_name }}</p>
          <p v-if="c.city" class="text-xs text-ink-600">{{ c.city }}</p>
        </RouterLink>
      </div>
    </section>

    <section class="rounded-2xl bg-sand p-8">
      <p class="text-xs font-semibold uppercase tracking-widest text-clay-700">
        {{ $t("dashboard.ctaEyebrow") }}
      </p>
      <h2 class="mt-2 text-2xl font-semibold">{{ $t("dashboard.ctaTitle") }}</h2>
      <p class="mt-2 max-w-md text-sm text-ink-600">{{ $t("dashboard.ctaBody") }}</p>
      <div class="mt-5 flex flex-wrap gap-3">
        <UButton to="/campaigns" size="lg">{{ $t("dashboard.startCampaign") }} →</UButton>
        <UButton to="/deck" size="lg" variant="outline" color="neutral" class="bg-white">
          {{ $t("dashboard.startSwiping") }}
        </UButton>
      </div>
    </section>

    <p class="text-center">
      <button
        type="button"
        class="text-sm text-ink-600 transition-colors hover:text-clay-700"
        @click="gameOpen = true"
      >
        🐸 {{ $t("kvaekker.tease") }}
      </button>
    </p>

    <KvaekkerGame v-model:open="gameOpen" />
  </main>
</template>
