<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

function signup() {
  sessionStorage.setItem("signup-intent", "creator");
  router.push("/auth");
}
</script>

<template>
  <main class="mx-auto flex max-w-2xl flex-col gap-10 px-6 pt-12 pb-14 sm:pt-16">
    <header class="flex flex-col items-center gap-4 text-center">
      <img src="/logo.png" alt="" class="h-20 w-20" />
      <h1 class="text-3xl font-semibold tracking-tight">{{ $t("forCreators.title") }}</h1>
      <p class="max-w-lg text-ink-600">{{ $t("forCreators.sub") }}</p>
    </header>

    <ol class="grid gap-4 sm:grid-cols-3">
      <li v-for="n in 3" :key="n" class="rounded-2xl bg-white p-5 shadow-sm">
        <span class="mb-2 flex h-8 w-8 items-center justify-center rounded-full bg-clay-100 font-semibold text-clay-700">
          {{ n }}
        </span>
        <h2 class="font-semibold">{{ $t(`forCreators.step${n}t`) }}</h2>
        <p class="mt-1 text-sm text-ink-600">{{ $t(`forCreators.step${n}d`) }}</p>
      </li>
    </ol>

    <UAlert color="primary" variant="subtle" :description="$t('forCreators.beta')" class="text-left" />

    <div class="flex flex-col items-center gap-3">
      <UButton size="xl" class="px-10" @click="signup">{{ $t("forCreators.cta") }}</UButton>
      <RouterLink to="/brands" class="text-sm text-ink-600 underline">{{ $t("forCreators.brandInstead") }}</RouterLink>
    </div>
  </main>
</template>
