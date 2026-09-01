<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import { allauth } from "../lib/api";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const toast = useToast();

const newPassword = ref("");
const repeatPassword = ref("");
const error = ref("");
const busy = ref(false);

async function submit() {
  error.value = "";
  if (newPassword.value !== repeatPassword.value) {
    error.value = t("account.passwordMismatch");
    return;
  }
  busy.value = true;
  try {
    const res = await allauth("POST", "/auth/password/reset", {
      key: route.params.key as string,
      password: newPassword.value,
    });
    if (res.status === 200 || (res.status === 401 && !res.data?.errors)) {
      toast.add({ title: t("reset.done"), color: "success" });
      router.push("/auth");
    } else {
      error.value = res.data?.errors?.[0]?.message ?? "Something went wrong";
    }
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <main class="mx-auto flex max-w-sm flex-col gap-6 px-6 pt-16 pb-10 sm:pt-24">
    <img src="/logo.png" alt="" class="mx-auto h-20 w-20" />
    <h1 class="text-center text-2xl font-semibold">{{ $t("reset.title") }}</h1>
    <form class="surface flex flex-col gap-4" @submit.prevent="submit">
      <UFormField :label="$t('account.newPassword')">
        <UInput v-model="newPassword" type="password" required autofocus size="xl" class="w-full" />
      </UFormField>
      <UFormField :label="$t('account.repeatPassword')">
        <UInput v-model="repeatPassword" type="password" required size="xl" class="w-full" />
      </UFormField>
      <UButton type="submit" :loading="busy" size="xl" block>{{ $t("reset.submit") }}</UButton>
    </form>
    <UAlert v-if="error" color="error" variant="outline" class="bg-white" :description="error" />
  </main>
</template>
