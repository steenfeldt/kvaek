<script setup lang="ts">
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { useSession } from "../stores/session";

// Landing page after a social login: pick up the fresh session cookie and
// route like any other login (new users go to onboarding with their intent).
const router = useRouter();
const session = useSession();

onMounted(async () => {
  await session.refresh();
  if (session.authenticated) {
    router.replace(session.postLoginRoute(sessionStorage.getItem("signup-intent") ?? undefined));
  } else {
    router.replace("/auth?error=social");
  }
});
</script>

<template>
  <main class="flex min-h-[60vh] items-center justify-center text-ink-600">
    {{ $t("auth.finishing") }}
  </main>
</template>
