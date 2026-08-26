<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { allauth } from "../lib/api";
import { useSession } from "../stores/session";

const router = useRouter();
const session = useSession();

const email = ref("");
const code = ref("");
const stage = ref<"email" | "code">("email");
// Explicit choice — the API is enumeration-safe and never reveals whether an
// account exists, so the user picks; a wrong pick gets an explanatory email.
// Arriving via a landing door implies a new account.
const mode = ref<"login" | "signup">(sessionStorage.getItem("signup-intent") ? "signup" : "login");
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

function switchMode(to?: string) {
  mode.value = to === "signup" || to === "login" ? to : mode.value === "login" ? "signup" : "login";
  stage.value = "email";
  code.value = "";
  error.value = "";
}
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-6 px-6">
    <img src="/logo.png" alt="" class="mx-auto h-20 w-20" />

    <div class="flex rounded-xl border border-clay-200 bg-white p-1 text-sm font-medium">
      <button
        class="flex-1 rounded-lg py-2"
        :class="mode === 'login' ? 'bg-clay-600 text-white' : 'text-ink-600'"
        @click="switchMode('login')"
      >
        {{ $t("auth.login") }}
      </button>
      <button
        class="flex-1 rounded-lg py-2"
        :class="mode === 'signup' ? 'bg-clay-600 text-white' : 'text-ink-600'"
        @click="switchMode('signup')"
      >
        {{ $t("auth.signup") }}
      </button>
    </div>

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
        {{ mode === "login" ? $t("auth.noCodeLogin") : $t("auth.noCodeSignup") }}
        <button type="button" class="underline" @click="switchMode()">
          {{ mode === "login" ? $t("auth.signup") : $t("auth.login") }}
        </button>
      </p>
    </form>

    <UAlert v-if="error" color="error" variant="subtle" :description="error" />
  </main>
</template>
