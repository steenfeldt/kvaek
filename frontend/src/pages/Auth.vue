<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { allauth } from "../lib/api";
import { useSession } from "../stores/session";

const router = useRouter();
const session = useSession();

const email = ref("");
const code = ref("");
const stage = ref<"email" | "code">("email");
// The mode is set by how you arrive: audience-page CTAs store a signup intent,
// everything else is a login. The API is enumeration-safe and never reveals
// whether an account exists; a wrong mode gets an explanatory email plus the
// hint under the code field.
const intent = computed(() => sessionStorage.getItem("signup-intent"));
const mode = ref<"login" | "signup">(intent.value ? "signup" : "login");
const error = ref("");
const busy = ref(false);

async function sendCode() {
  error.value = "";
  busy.value = true;
  try {
    const res =
      mode.value === "signup"
        ? await allauth("POST", "/auth/signup", { email: email.value })
        : await allauth("POST", "/auth/code/request", { email: email.value });
    if (res.status === 401 || res.status === 200) {
      stage.value = "code";
    } else {
      error.value = res.data?.errors?.[0]?.message ?? "Something went wrong";
    }
  } finally {
    busy.value = false;
  }
}

async function confirmCode() {
  error.value = "";
  busy.value = true;
  try {
    const value = code.value.trim().toUpperCase();
    const res =
      mode.value === "login"
        ? await allauth("POST", "/auth/code/confirm", { code: value })
        : await allauth("POST", "/auth/email/verify", { key: value });
    if (res.status === 200 || res.data?.meta?.is_authenticated) {
      await session.refresh();
      router.push(session.postLoginRoute(sessionStorage.getItem("signup-intent") ?? undefined));
    } else {
      error.value = res.data?.errors?.[0]?.message ?? "Invalid code";
    }
  } finally {
    busy.value = false;
  }
}

function toLogin() {
  mode.value = "login";
  stage.value = "email";
  code.value = "";
  error.value = "";
}
</script>

<template>
  <main class="mx-auto flex max-w-sm flex-col gap-6 px-6 pt-16 pb-10 sm:pt-24">
    <img src="/logo.png" alt="" class="mx-auto h-20 w-20" />

    <header class="text-center">
      <h1 class="text-2xl font-semibold">
        {{ mode === "login" ? $t("auth.login") : $t("auth.signup") }}
      </h1>
      <p v-if="mode === 'signup' && intent" class="mt-1 text-sm text-ink-600">
        {{ intent === "creator" ? $t("auth.asCreator") : $t("auth.asBrand") }}
      </p>
    </header>

    <form v-if="stage === 'email'" class="flex flex-col gap-4" @submit.prevent="sendCode">
      <UFormField :label="$t('auth.emailLabel')">
        <UInput v-model="email" type="email" required autofocus size="xl" class="w-full" />
      </UFormField>
      <UButton type="submit" :loading="busy" size="xl" block>{{ $t("auth.sendCode") }}</UButton>
    </form>

    <form v-else class="flex flex-col gap-4" @submit.prevent="confirmCode">
      <p class="text-sm text-ink-600">{{ $t("auth.sentTo", { email }) }}</p>
      <UFormField :label="$t('auth.codeLabel')">
        <UInput
          v-model="code"
          required
          autofocus
          size="xl"
          class="w-full"
          :ui="{ base: 'text-center text-xl tracking-widest uppercase' }"
        />
      </UFormField>
      <UButton type="submit" :loading="busy" size="xl" block>{{ $t("auth.confirm") }}</UButton>
      <p class="text-sm text-ink-600">
        <template v-if="mode === 'login'">
          {{ $t("auth.noCodeLogin") }}
          <RouterLink to="/" class="underline">{{ $t("auth.getStarted") }}</RouterLink>
        </template>
        <template v-else>
          {{ $t("auth.noCodeSignup") }}
          <button type="button" class="underline" @click="toLogin">{{ $t("auth.login") }}</button>
        </template>
      </p>
    </form>

    <p class="text-center text-sm text-ink-600">
      <template v-if="mode === 'login'">
        {{ $t("auth.newHere") }}
        <RouterLink to="/" class="font-medium text-clay-700 underline">{{ $t("auth.getStarted") }}</RouterLink>
      </template>
      <template v-else>
        {{ $t("landing.haveAccount") }}
        <button type="button" class="font-medium text-clay-700 underline" @click="toLogin">
          {{ $t("auth.login") }}
        </button>
      </template>
    </p>

    <UAlert v-if="error" color="error" variant="subtle" :description="error" />
  </main>
</template>
