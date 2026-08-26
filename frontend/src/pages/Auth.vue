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
// "login" = existing account (login-by-code); "signup" = new account (verify-email code).
const mode = ref<"login" | "signup">("login");
const error = ref("");
const busy = ref(false);

async function sendCode() {
  error.value = "";
  busy.value = true;
  try {
    // Signup first; an existing account falls through to a login code.
    // Exactly one email is sent either way.
    const signup = await allauth("POST", "/auth/signup", { email: email.value });
    if (signup.status === 401 || signup.status === 200) {
      mode.value = "signup";
      stage.value = "code";
      return;
    }
    const errors: { code: string; message: string }[] = signup.data?.errors ?? [];
    if (errors.some((e) => e.code === "email_taken")) {
      const login = await allauth("POST", "/auth/code/request", { email: email.value });
      if (login.status === 401 || login.status === 200) {
        mode.value = "login";
        stage.value = "code";
      } else {
        error.value = login.data?.errors?.[0]?.message ?? "Something went wrong";
      }
    } else {
      error.value = errors[0]?.message ?? "Something went wrong";
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
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-6 px-6">
    <h1 class="text-2xl font-semibold">{{ $t("auth.title") }}</h1>

    <form v-if="stage === 'email'" class="flex flex-col gap-3" @submit.prevent="sendCode">
      <label class="text-sm text-ink-600">{{ $t("auth.emailLabel") }}</label>
      <input
        v-model="email"
        type="email"
        required
        autofocus
        class="rounded-lg border border-clay-200 bg-white px-4 py-3"
      />
      <button :disabled="busy" class="rounded-lg bg-clay-600 py-3 font-medium text-white hover:bg-clay-700">
        {{ $t("auth.sendCode") }}
      </button>
    </form>

    <form v-else class="flex flex-col gap-3" @submit.prevent="confirmCode">
      <p class="text-sm text-ink-600">{{ $t("auth.sentTo", { email }) }}</p>
      <label class="text-sm text-ink-600">{{ $t("auth.codeLabel") }}</label>
      <input
        v-model="code"
        inputmode="numeric"
        required
        autofocus
        class="rounded-lg border border-clay-200 bg-white px-4 py-3 text-center text-xl tracking-widest"
      />
      <button :disabled="busy" class="rounded-lg bg-clay-600 py-3 font-medium text-white hover:bg-clay-700">
        {{ $t("auth.confirm") }}
      </button>
    </form>

    <p v-if="error" class="text-sm text-red-700">{{ error }}</p>
  </main>
</template>
