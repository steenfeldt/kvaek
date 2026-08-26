<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

function go(role: "brand" | "creator") {
  router.push(role === "brand" ? "/brands" : "/creators");
}

function login() {
  sessionStorage.removeItem("signup-intent");
  router.push("/auth");
}
</script>

<template>
  <main class="mx-auto flex max-w-xl flex-col items-center gap-10 px-6 pt-16 pb-12 text-center sm:pt-24">
    <img src="/logo.png" alt="" class="h-36 w-36" />
    <h1 class="text-4xl font-semibold tracking-tight">{{ $t("landing.tagline") }}</h1>
    <div class="grid w-full gap-4 sm:grid-cols-2">
      <button
        class="rounded-2xl bg-clay-600 p-6 text-left text-white transition hover:bg-clay-700"
        @click="go('brand')"
      >
        <span class="block text-xl font-semibold">{{ $t("landing.brandCta") }}</span>
        <span class="mt-2 block text-sm opacity-80">{{ $t("landing.brandSub") }}</span>
      </button>
      <button
        class="rounded-2xl border-2 border-clay-200 bg-white p-6 text-left transition hover:border-clay-500"
        @click="go('creator')"
      >
        <span class="block text-xl font-semibold">{{ $t("landing.creatorCta") }}</span>
        <span class="mt-2 block text-sm text-ink-600">{{ $t("landing.creatorSub") }}</span>
      </button>
    </div>
    <p class="text-sm text-ink-600">
      {{ $t("landing.haveAccount") }}
      <button class="font-medium text-clay-700 underline" @click="login">{{ $t("auth.login") }}</button>
    </p>
  </main>
</template>
