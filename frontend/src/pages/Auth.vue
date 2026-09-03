<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import { allauth, ensureCsrf, getCookie } from "../lib/api";
import { useSession } from "../stores/session";

const router = useRouter();
const route = useRoute();
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
// Code login is the default; a password is an opt-in alternative for login.
const usePassword = ref(false);
const password = ref("");
const info = ref("");
const error = ref("");
const busy = ref(false);
const { t } = useI18n();
if (route.query.error === "social") error.value = t("auth.socialError");

// Google: a real form POST so the browser follows allauth's redirect to
// Google and back to /auth/callback. The signup intent survives in
// sessionStorage across the round trip.
async function continueWithGoogle() {
  await ensureCsrf();
  const form = document.createElement("form");
  form.method = "POST";
  form.action = "/_allauth/browser/v1/auth/provider/redirect";
  const fields: Record<string, string> = {
    provider: "google",
    callback_url: `${window.location.origin}/auth/callback`,
    process: "login",
    csrfmiddlewaretoken: getCookie("csrftoken") ?? "",
  };
  for (const [name, value] of Object.entries(fields)) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.appendChild(input);
  }
  document.body.appendChild(form);
  form.submit();
}

async function loginWithPassword() {
  error.value = "";
  busy.value = true;
  try {
    const res = await allauth("POST", "/auth/login", { email: email.value, password: password.value });
    if (res.status === 200 || res.data?.meta?.is_authenticated) {
      await session.refresh();
      router.push(session.postLoginRoute());
    } else {
      error.value = res.data?.errors?.[0]?.message ?? "Something went wrong";
    }
  } finally {
    busy.value = false;
  }
}

async function forgotPassword() {
  if (!email.value) {
    error.value = t("auth.forgotNeedsEmail");
    return;
  }
  error.value = "";
  await allauth("POST", "/auth/password/request", { email: email.value });
  info.value = t("auth.forgotSent");
}

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

    <form
      v-if="stage === 'email'"
      class="surface flex flex-col gap-4"
      @submit.prevent="usePassword ? loginWithPassword() : sendCode()"
    >
      <UButton type="button" variant="outline" color="neutral" size="xl" block class="bg-white" @click="continueWithGoogle">
        <UIcon name="simple-icons:google" class="size-4" />
        {{ $t("auth.google") }}
      </UButton>
      <div class="flex items-center gap-3 text-xs text-ink-500">
        <span class="h-px flex-1 bg-clay-200" />
        {{ $t("auth.or") }}
        <span class="h-px flex-1 bg-clay-200" />
      </div>
      <UFormField :label="$t('auth.emailLabel')">
        <UInput v-model="email" type="email" required autofocus size="xl" class="w-full" />
      </UFormField>
      <UFormField v-if="usePassword" :label="$t('auth.passwordLabel')">
        <UInput v-model="password" type="password" required size="xl" class="w-full" />
      </UFormField>
      <UButton type="submit" :loading="busy" size="xl" block>
        {{ usePassword ? $t("auth.login") : $t("auth.sendCode") }}
      </UButton>
      <p v-if="mode === 'login'" class="text-center text-sm text-ink-600">
        <template v-if="!usePassword">
          <button type="button" class="underline" @click="usePassword = true">
            {{ $t("auth.loginWithPassword") }}
          </button>
        </template>
        <template v-else>
          <button type="button" class="underline" @click="usePassword = false">
            {{ $t("auth.useCodeInstead") }}
          </button>
          ·
          <button type="button" class="underline" @click="forgotPassword">
            {{ $t("auth.forgotPassword") }}
          </button>
        </template>
      </p>
    </form>

    <form v-else class="surface flex flex-col gap-4" @submit.prevent="confirmCode">
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
        <RouterLink to="/" class="font-medium text-fjord-700 underline">{{ $t("auth.getStarted") }}</RouterLink>
      </template>
      <template v-else>
        {{ $t("landing.haveAccount") }}
        <button type="button" class="font-medium text-fjord-700 underline" @click="toLogin">
          {{ $t("auth.login") }}
        </button>
      </template>
    </p>

    <UAlert v-if="info" color="info" variant="outline" class="bg-white" :description="info" />
    <UAlert v-if="error" color="error" variant="outline" class="bg-white" :description="error" />
  </main>
</template>
