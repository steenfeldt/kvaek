<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { ref } from "vue";
import KvaekkerGame from "../components/KvaekkerGame.vue";
import { api } from "../lib/api";
import { useGreeting } from "../lib/greeting";

interface CreatorDashboard {
  display_name: string;
  city: string;
  waiting_briefs: number;
  deals_in_flight: number;
  listed: boolean;
  profile_complete: boolean;
}

const { data } = useQuery({
  queryKey: ["creator-dashboard"],
  queryFn: () => api<CreatorDashboard>("/dashboard/creator"),
});
const { data: saved } = useQuery({
  queryKey: ["saved-count"],
  queryFn: () => api<{ saved_last_7_days: number }>("/creator/saved-count"),
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
        {{ greeting }}, <span class="text-clay-700">{{ data.display_name }}</span
        >.
      </h1>
      <p v-if="data.city" class="mt-1 text-sm text-ink-600">{{ data.city }}</p>
    </header>

    <section
      v-if="data"
      class="grid grid-cols-1 divide-y divide-clay-200 border-y border-clay-200 sm:grid-cols-3 sm:divide-x sm:divide-y-0"
    >
      <RouterLink to="/briefs" class="px-5 py-6 transition-colors hover:bg-cream">
        <p class="text-xs font-semibold uppercase tracking-widest text-ink-600">
          {{ $t("dashboard.waitingOnYou") }}
        </p>
        <p class="mt-2 text-4xl font-semibold text-clay-600">{{ data.waiting_briefs }}</p>
        <p class="mt-1 text-sm text-ink-600">{{ $t("creatorDash.waitingSub") }}</p>
      </RouterLink>
      <RouterLink to="/deals" class="px-5 py-6 transition-colors hover:bg-cream">
        <p class="text-xs font-semibold uppercase tracking-widest text-ink-600">
          {{ $t("dashboard.dealsInFlight") }}
        </p>
        <p class="mt-2 text-4xl font-semibold text-sage-600">{{ data.deals_in_flight }}</p>
        <p class="mt-1 text-sm text-ink-600">{{ $t("dashboard.dealsSub") }}</p>
      </RouterLink>
      <RouterLink to="/profile" class="px-5 py-6 transition-colors hover:bg-cream">
        <p class="text-xs font-semibold uppercase tracking-widest text-ink-600">
          {{ $t("creatorDash.saved") }}
        </p>
        <p class="mt-2 text-4xl font-semibold text-fjord-600">{{ saved?.saved_last_7_days ?? "–" }}</p>
        <p class="mt-1 text-sm text-ink-600">{{ $t("creatorDash.savedSub") }}</p>
      </RouterLink>
    </section>

    <section
      v-if="data"
      class="rounded-2xl bg-white p-8"
    >
      <p class="text-xs font-semibold uppercase tracking-widest text-clay-700">
        {{ $t("dashboard.ctaEyebrow") }}
      </p>
      <template v-if="data.listed">
        <h2 class="mt-2 text-2xl font-semibold">{{ $t("creatorDash.ctaListedTitle") }}</h2>
        <p class="mt-2 max-w-md text-sm text-ink-600">{{ $t("creatorDash.ctaListedBody") }}</p>
        <div class="mt-5 flex flex-wrap gap-3">
          <UButton to="/briefs" size="lg">{{ $t("creatorDash.seeBriefs") }} →</UButton>
          <UButton to="/profile" size="lg" variant="outline" color="neutral" class="bg-white">
            {{ $t("creatorDash.seeProfile") }}
          </UButton>
        </div>
      </template>
      <template v-else>
        <h2 class="mt-2 text-2xl font-semibold">{{ $t("creatorDash.ctaNotListedTitle") }}</h2>
        <p class="mt-2 max-w-md text-sm text-ink-600">{{ $t("creatorDash.ctaNotListedBody") }}</p>
        <div class="mt-5">
          <UButton to="/profile" size="lg">{{ $t("creatorDash.completeProfile") }} →</UButton>
        </div>
      </template>
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
