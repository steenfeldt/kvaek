<script setup lang="ts">
import { da, en } from "@nuxt/ui/locale";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { allauth } from "./lib/api";
import { useSession } from "./stores/session";

const session = useSession();
const router = useRouter();
const { locale } = useI18n();
const uiLocale = computed(() => (locale.value === "da" ? da : en));

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
  <UApp :locale="uiLocale">
    <div class="min-h-screen">
      <header v-if="session.authenticated && session.role" class="border-b border-clay-200 bg-white">
        <nav class="mx-auto flex max-w-3xl items-center gap-2 px-4 py-2 text-sm">
          <RouterLink :to="session.role === 'brand' ? '/deck' : '/home'" class="mr-2">
            <img src="/logo.png" alt="Kvæk" class="h-8 w-8 rounded-lg" />
          </RouterLink>
          <template v-if="session.role === 'brand'">
            <UButton to="/deck" variant="ghost" color="neutral" class="navlink">{{ $t("nav.deck") }}</UButton>
            <UButton to="/campaigns" variant="ghost" color="neutral" class="navlink">{{ $t("nav.campaigns") }}</UButton>
          </template>
          <template v-else>
            <UButton to="/home" variant="ghost" color="neutral" class="navlink">{{ $t("nav.home") }}</UButton>
            <UButton to="/profile" variant="ghost" color="neutral" class="navlink">{{ $t("nav.profile") }}</UButton>
          </template>
          <UButton to="/briefs" variant="ghost" color="neutral" class="navlink">{{ $t("nav.briefs") }}</UButton>
          <UButton to="/deals" variant="ghost" color="neutral" class="navlink">{{ $t("nav.deals") }}</UButton>
          <span class="flex-1" />
          <UButton variant="ghost" color="neutral" size="sm" @click="toggleLocale">
            {{ locale === "da" ? "EN" : "DA" }}
          </UButton>
          <UButton variant="ghost" color="neutral" size="sm" @click="logout">{{ $t("nav.logout") }}</UButton>
        </nav>
      </header>
      <RouterView />
    </div>
  </UApp>
</template>

<style scoped>
@reference "./style.css";
.navlink.router-link-active {
  @apply font-semibold text-clay-700;
}
</style>
