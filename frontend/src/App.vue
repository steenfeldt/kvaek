<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { allauth } from "./lib/api";
import { useSession } from "./stores/session";

const session = useSession();
const router = useRouter();
const { locale } = useI18n();

async function logout() {
  await allauth("DELETE", "/auth/session");
  session.me = null;
  session.loaded = false;
  router.push("/");
}

function toggleLocale() {
  locale.value = locale.value === "da" ? "en" : "da";
}
</script>

<template>
  <div class="min-h-screen">
    <header v-if="session.authenticated && session.role" class="border-b border-clay-200 bg-white">
      <nav class="mx-auto flex max-w-3xl items-center gap-5 px-4 py-3 text-sm">
        <template v-if="session.role === 'brand'">
          <RouterLink to="/deck" class="navlink">{{ $t("nav.deck") }}</RouterLink>
          <RouterLink to="/campaigns" class="navlink">{{ $t("nav.campaigns") }}</RouterLink>
        </template>
        <template v-else>
          <RouterLink to="/home" class="navlink">{{ $t("nav.home") }}</RouterLink>
          <RouterLink to="/profile" class="navlink">{{ $t("nav.profile") }}</RouterLink>
        </template>
        <RouterLink to="/briefs" class="navlink">{{ $t("nav.briefs") }}</RouterLink>
        <RouterLink to="/deals" class="navlink">{{ $t("nav.deals") }}</RouterLink>
        <span class="flex-1" />
        <button class="text-ink-600 hover:text-ink-900" @click="toggleLocale">
          {{ locale === "da" ? "EN" : "DA" }}
        </button>
        <button class="text-ink-600 hover:text-ink-900" @click="logout">{{ $t("nav.logout") }}</button>
      </nav>
    </header>
    <RouterView />
  </div>
</template>

<style scoped>
@reference "./style.css";
.navlink {
  @apply text-ink-600 hover:text-ink-900;
}
.navlink.router-link-active {
  @apply font-semibold text-clay-700;
}
</style>
